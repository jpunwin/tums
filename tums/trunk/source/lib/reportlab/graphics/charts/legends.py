#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/legends.py
"""This will be a collection of legends to be used with charts.
"""
__version__=''' $Id: legends.py 3147 2007-09-28 12:52:01Z rgbecker $ '''

import copy, operator

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, OneOf, isString, isColorOrNone,\
        isNumberOrNone, isListOfNumbersOrNone, isStringOrNone, isBoolean,\
        EitherOr, NoneOr, AutoOr, isAuto, Auto, isBoxAnchor, SequenceOf, isInstanceOf
from reportlab.lib.attrmap import *
from reportlab.pdfbase.pdfmetrics import stringWidth, getFont
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.shapes import Drawing, Group, String, Rect, Line, STATE_DEFAULTS
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol
from reportlab.lib.utils import isSeqType, find_locals

def _transMax(n,A):
    X = n*[0]
    m = 0
    for a in A:
        m = max(m,len(a))
        for i,x in enumerate(a):
            X[i] = max(X[i],x)
    X = [0] + X[:m]
    for i in xrange(m):
        X[i+1] += X[i]
    return X

def _objStr(s):
    if isinstance(s,basestring):
        return s
    else:
        return str(s)

def _getStr(s):
    if isSeqType(s):
        return map(_getStr,s)
    else:
        return _objStr(s)

def _getLines(s):
    if isSeqType(s):
        return tuple([(x or '').split('\n') for x in s])
    else:
        return (s or '').split('\n')

def _getLineCount(s):
    T = _getLines(s)
    if isSeqType(s):
        return max([len(x) for x in T])
    else:
        return len(T)

def _getWidths(i,s, fontName, fontSize, subCols):
    S = []
    aS = S.append
    if isSeqType(s):
        for j,t in enumerate(s):
            sc = subCols[j,i]
            fN = getattr(sc,'fontName',fontName)
            fS = getattr(sc,'fontSize',fontSize)
            m = [stringWidth(x, fN, fS) for x in t.split('\n')]
            m = max(sc.minWidth,m and max(m) or 0)
            aS(m)
            aS(sc.rpad)
        del S[-1]
    else:
        sc = subCols[0,i]
        fN = getattr(sc,'fontName',fontName)
        fS = getattr(sc,'fontSize',fontSize)
        m = [stringWidth(x, fN, fS) for x in s.split('\n')]
        aS(max(subCols[0,i],m and max(m) or 0))
    return S

class SubColProperty(PropHolder):
    dividerLines = 0
    _attrMap = AttrMap(
        minWidth = AttrMapValue(isNumber,desc="minimum width for this subcol"),
        rpad = AttrMapValue(isNumber,desc="right padding for this subcol"),
        align = AttrMapValue(OneOf('left','right','center','centre'),desc='alignment in subCol'),
        fontName = AttrMapValue(isString, desc="Font name of the strings"),
        fontSize = AttrMapValue(isNumber, desc="Font size of the strings"),
        leading = AttrMapValue(isNumber, desc="leading for the strings"),
        fillColor = AttrMapValue(isColorOrNone, desc="fontColor"),
        underlines = AttrMapValue(EitherOr((NoneOr(isInstanceOf(Line)),SequenceOf(isInstanceOf(Line),emptyOK=0,lo=0,hi=0x7fffffff))), desc="underline definitions"),
        overlines = AttrMapValue(EitherOr((NoneOr(isInstanceOf(Line)),SequenceOf(isInstanceOf(Line),emptyOK=0,lo=0,hi=0x7fffffff))), desc="overline definitions"),
        )

class LegendCallout:
    def _legendValues(legend,*args):
        '''return a tuple of values from the first function up the stack with isinstance(self,legend)'''
        L = find_locals(lambda L: L.get('self',None) is legend and L or None)
        return tuple([L[a] for a in args])
    _legendValues = staticmethod(_legendValues)

    def _selfOrLegendValues(self,legend,*args):
        L = find_locals(lambda L: L.get('self',None) is legend and L or None)
        return tuple([getattr(self,a,L[a]) for a in args])

    def __call__(self,legend,g,thisx,y,(col,name)):
        pass

class LegendColEndCallout(LegendCallout):
    def __call__(self,legend, g, x, xt, y, width, lWidth):
        pass

class Legend(Widget):
    """A simple legend containing rectangular swatches and strings.

    The swatches are filled rectangles whenever the respective
    color object in 'colorNamePairs' is a subclass of Color in
    reportlab.lib.colors. Otherwise the object passed instead is
    assumed to have 'x', 'y', 'width' and 'height' attributes.
    A legend then tries to set them or catches any error. This
    lets you plug-in any widget you like as a replacement for
    the default rectangular swatches.

    Strings can be nicely aligned left or right to the swatches.
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x-coordinate of upper-left reference point"),
        y = AttrMapValue(isNumber, desc="y-coordinate of upper-left reference point"),
        deltax = AttrMapValue(isNumberOrNone, desc="x-distance between neighbouring swatches"),
        deltay = AttrMapValue(isNumberOrNone, desc="y-distance between neighbouring swatches"),
        dxTextSpace = AttrMapValue(isNumber, desc="Distance between swatch rectangle and text"),
        autoXPadding = AttrMapValue(isNumber, desc="x Padding between columns if deltax=None"),
        autoYPadding = AttrMapValue(isNumber, desc="y Padding between rows if deltay=None"),
        yGap = AttrMapValue(isNumber, desc="Additional gap between rows"),
        dx = AttrMapValue(isNumber, desc="Width of swatch rectangle"),
        dy = AttrMapValue(isNumber, desc="Height of swatch rectangle"),
        columnMaximum = AttrMapValue(isNumber, desc="Max. number of items per column"),
        alignment = AttrMapValue(OneOf("left", "right"), desc="Alignment of text with respect to swatches"),
        colorNamePairs = AttrMapValue(None, desc="List of color/name tuples (color can also be widget)"),
        fontName = AttrMapValue(isString, desc="Font name of the strings"),
        fontSize = AttrMapValue(isNumber, desc="Font size of the strings"),
        fillColor = AttrMapValue(isColorOrNone, desc=""),
        strokeColor = AttrMapValue(isColorOrNone, desc="Border color of the swatches"),
        strokeWidth = AttrMapValue(isNumber, desc="Width of the border color of the swatches"),
        swatchMarker = AttrMapValue(NoneOr(AutoOr(isSymbol)), desc="None, Auto() or makeMarker('Diamond') ..."),
        callout = AttrMapValue(None, desc="a user callout(self,g,x,y,(color,text))"),
        boxAnchor = AttrMapValue(isBoxAnchor,'Anchor point for the legend area'),
        variColumn = AttrMapValue(isBoolean,'If true column widths may vary (default is false)'),
        dividerLines = AttrMapValue(OneOf(0,1,2,3,4,5,6,7),'If 1 we have dividers between the rows | 2 for extra top | 4 for bottom'),
        dividerWidth = AttrMapValue(isNumber, desc="dividerLines width"),
        dividerColor = AttrMapValue(isColorOrNone, desc="dividerLines color"),
        dividerDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array for dividerLines.'),
        dividerOffsX = AttrMapValue(SequenceOf(isNumber,emptyOK=0,lo=2,hi=2), desc='divider lines X offsets'),
        dividerOffsY = AttrMapValue(isNumber, desc="dividerLines Y offset"),
        colEndCallout = AttrMapValue(None, desc="a user callout(self,g, x, xt, y,width, lWidth)"),
        subCols = AttrMapValue(None,desc="subColumn properties"),
       )

    def __init__(self):
        # Upper-left reference point.
        self.x = 0
        self.y = 0

        # Alginment of text with respect to swatches.
        self.alignment = "left"

        # x- and y-distances between neighbouring swatches.
        self.deltax = 75
        self.deltay = 20
        self.autoXPadding = 5
        self.autoYPadding = 2

        # Size of swatch rectangle.
        self.dx = 10
        self.dy = 10

        # Distance between swatch rectangle and text.
        self.dxTextSpace = 10

        # Max. number of items per column.
        self.columnMaximum = 3

        # Color/name pairs.
        self.colorNamePairs = [ (colors.red, "red"),
                                (colors.blue, "blue"),
                                (colors.green, "green"),
                                (colors.pink, "pink"),
                                (colors.yellow, "yellow") ]

        # Font name and size of the labels.
        self.fontName = STATE_DEFAULTS['fontName']
        self.fontSize = STATE_DEFAULTS['fontSize']
        self.fillColor = STATE_DEFAULTS['fillColor']
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeWidth = STATE_DEFAULTS['strokeWidth']
        self.swatchMarker = None
        self.boxAnchor = 'nw'
        self.yGap = 0
        self.variColumn = 0
        self.dividerLines = 0
        self.dividerWidth = 0.5
        self.dividerDashArray = None
        self.dividerColor = colors.black
        self.dividerOffsX = (0,0)
        self.dividerOffsY = 0
        self.colEndCallout = None
        self._init_subCols()

    def _init_subCols(self):
        sc = self.subCols = TypedPropertyCollection(SubColProperty)
        sc.rpad = 1
        sc.minWidth = 0
        sc.align = 'right'
        sc[0].align = 'left' 

    def _getChartStyleName(self,chart):
        for a in 'lines', 'bars', 'slices', 'strands':
            if hasattr(chart,a): return a
        return None

    def _getChartStyle(self,chart):
        return getattr(chart,self._getChartStyleName(chart),None)
        
    def _getTexts(self,colorNamePairs):
        if not isAuto(colorNamePairs):
            texts = [_getStr(p[1]) for p in colorNamePairs]
        else:
            chart = colorNamePairs.chart
            texts = [chart.getSeriesName(i,'series %d' % i) for i in xrange(chart._seriesCount)]
        return texts

    def _calculateMaxBoundaries(self, colorNamePairs):
        "Calculate the maximum width of some given strings."
        fontName = self.fontName
        fontSize = self.fontSize
        subCols = self.subCols

        M = [_getWidths(i, m, fontName, fontSize, subCols) for i,m in enumerate(self._getTexts(colorNamePairs))]
        if not M:
            return [0,0]
        n = max([len(m) for m in M])
        if self.variColumn:
            columnMaximum = self.columnMaximum
            return [_transMax(n,M[r:r+columnMaximum]) for r in xrange(0,len(M),self.columnMaximum)]
        else:
            return _transMax(n,M)

    def _calcHeight(self):
        dy = self.dy
        yGap = self.yGap
        thisy = upperlefty = self.y - dy
        fontSize = self.fontSize
        ascent=getFont(self.fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize
        leading = fontSize*1.2
        deltay = self.deltay
        if not deltay: deltay = max(dy,leading)+self.autoYPadding
        columnCount = 0
        count = 0
        lowy = upperlefty
        lim = self.columnMaximum - 1
        for name in self._getTexts(self.colorNamePairs):
            y0 = thisy+(dy-ascent)*0.5
            y = y0 - _getLineCount(name)*leading
            leadingMove = 2*y0-y-thisy
            newy = thisy-max(deltay,leadingMove)-yGap
            lowy = min(y,newy,lowy)
            if count==lim:
                count = 0
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = newy
                count = count+1
        return upperlefty - lowy

    def _defaultSwatch(self,x,thisy,dx,dy,fillColor,strokeWidth,strokeColor):
        return Rect(x, thisy, dx, dy,
                    fillColor = fillColor,
                    strokeColor = strokeColor,
                    strokeWidth = strokeWidth,
                    )

    def draw(self):
        colorNamePairs = self.colorNamePairs
        autoCP = isAuto(colorNamePairs)
        if autoCP:
            chart = getattr(colorNamePairs,'chart',getattr(colorNamePairs,'obj',None))
            swatchMarker = None
            autoCP = Auto(obj=chart)
            n = chart._seriesCount
            chartTexts = self._getTexts(colorNamePairs)
        else:
            swatchMarker = getattr(self,'swatchMarker',None)
            if isAuto(swatchMarker):
                chart = getattr(swatchMarker,'chart',getattr(swatchMarker,'obj',None))
                swatchMarker = Auto(obj=chart)
            n = len(colorNamePairs)
        dx = self.dx
        dy = self.dy
        alignment = self.alignment
        columnMaximum = self.columnMaximum
        deltax = self.deltax
        deltay = self.deltay
        dxTextSpace = self.dxTextSpace
        fontName = self.fontName
        fontSize = self.fontSize
        fillColor = self.fillColor
        strokeWidth = self.strokeWidth
        strokeColor = self.strokeColor
        subCols = self.subCols
        leading = fontSize*1.2
        yGap = self.yGap
        if not deltay:
            deltay = max(dy,leading)+self.autoYPadding
        ba = self.boxAnchor
        maxWidth = self._calculateMaxBoundaries(colorNamePairs)
        nCols = int((n+columnMaximum-1)/columnMaximum)
        xW = dx+dxTextSpace+self.autoXPadding
        variColumn = self.variColumn
        if variColumn:
            width = reduce(operator.add,[m[-1] for m in maxWidth],0)+xW*nCols
        else:
            deltax = max(maxWidth[-1]+xW,deltax)
            width = maxWidth[-1]+nCols*deltax
            maxWidth = nCols*[maxWidth]

        thisx = self.x
        thisy = self.y - self.dy
        if ba not in ('ne','n','nw','autoy'):
            height = self._calcHeight()
            if ba in ('e','c','w'):
                thisy += height/2.
            else:
                thisy += height
        if ba not in ('nw','w','sw','autox'):
            if ba in ('n','c','s'):
                thisx -= width/2
            else:
                thisx -= width
        upperlefty = thisy

        g = Group()

        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize # normalize

        lim = columnMaximum - 1
        callout = getattr(self,'callout',None)
        dividerLines = self.dividerLines
        if dividerLines:
            dividerWidth = self.dividerWidth
            dividerColor = self.dividerColor
            dividerDashArray = self.dividerDashArray
            dividerOffsX = self.dividerOffsX
            dividerOffsY = self.dividerOffsY

        for i in xrange(n):
            if autoCP:
                col = autoCP
                col.index = i
                name = chartTexts[i]
            else:
                col, name = colorNamePairs[i]
                if isAuto(swatchMarker):
                    col = swatchMarker
                    col.index = i
                if isAuto(name):
                    name = getattr(swatchMarker,'chart',getattr(swatchMarker,'obj',None)).getSeriesName(i,'series %d' % i)
            T = _getLines(name)
            S = []
            aS = S.append
            j = int(i/columnMaximum)
            jOffs = maxWidth[j]

            # thisy+dy/2 = y+leading/2
            y = y0 = thisy+(dy-ascent)*0.5

            if callout: callout(self,g,thisx,y,(col,name))
            if alignment == "left":
                x = thisx
                xn = thisx+jOffs[-1]+dxTextSpace
            elif alignment == "right":
                x = thisx+dx+dxTextSpace
                xn = thisx
            else:
                raise ValueError, "bad alignment"
            if not isSeqType(name):
                T = [T]
            yd = y
            for k,lines in enumerate(T):
                y = y0
                kk = k*2
                x1 = x+jOffs[kk]
                x2 = x+jOffs[kk+1]
                sc = subCols[k,i]
                anchor = sc.align
                if anchor=='left':
                    anchor = 'start'
                    xoffs = x1
                elif anchor=='right':
                    anchor = 'end'
                    xoffs = x2
                else:
                    anchor = 'middle'
                    xoffs = 0.5*(x1+x2)
                fN = getattr(sc,'fontName',fontName)
                fS = getattr(sc,'fontSize',fontSize)
                fC = getattr(sc,'fillColor',fillColor)
                fL = getattr(sc,'leading',1.2*fontSize)
                if fN==fontName:
                    fA = (ascent*fS)/fontSize
                else:
                    fA = getFont(fontName).face.ascent/1000.
                    if fA==0: fA=0.718
                    fA *= fS
                for t in lines:
                    aS(String(xoffs,y,t,fontName=fN,fontSize=fS,fillColor=fC, textAnchor = anchor))
                    y -= fL
                yd = min(yd,y)
                y += fL
                for iy, a in ((y-max(fL-fA,0),'underlines'),(y+fA,'overlines')):
                    il = getattr(sc,a,None)
                    if il:
                        if not isinstance(il,(tuple,list)): il = (il,)
                        for l in il:
                            l = copy.copy(l)
                            l.y1 += iy
                            l.y2 += iy
                            l.x1 += x1
                            l.x2 += x2
                            aS(l)
            x = xn
            y = yd
            leadingMove = 2*y0-y-thisy

            if dividerLines:
                xd = thisx+dx+dxTextSpace+jOffs[-1]+dividerOffsX[1]
                yd = thisy+dy*0.5+dividerOffsY
                if ((dividerLines&1) and i%columnMaximum) or ((dividerLines&2) and not i%columnMaximum):
                    g.add(Line(thisx+dividerOffsX[0],yd,xd,yd,
                        strokeColor=dividerColor, strokeWidth=dividerWidth, strokeDashArray=dividerDashArray))

                if (dividerLines&4) and (i%columnMaximum==lim or i==(n-1)):
                    yd -= max(deltay,leadingMove)+yGap
                    g.add(Line(thisx+dividerOffsX[0],yd,xd,yd,
                        strokeColor=dividerColor, strokeWidth=dividerWidth, strokeDashArray=dividerDashArray))

            # Make a 'normal' color swatch...
            if isAuto(col):
                chart = getattr(col,'chart',getattr(col,'obj',None))
                g.add(chart.makeSwatchSample(getattr(col,'index',i),x,thisy,dx,dy))
            elif isinstance(col, colors.Color):
                if isSymbol(swatchMarker):
                    g.add(uSymbol2Symbol(swatchMarker,x+dx/2.,thisy+dy/2.,col))
                else:
                    g.add(self._defaultSwatch(x,thisy,dx,dy,fillColor=col,strokeWidth=strokeWidth,strokeColor=strokeColor))
            elif col is not None:
                try:
                    c = copy.deepcopy(col)
                    c.x = x
                    c.y = thisy
                    c.width = dx
                    c.height = dy
                    g.add(c)
                except:
                    pass

            map(g.add,S)
            if self.colEndCallout and (i%columnMaximum==lim or i==(n-1)):
                if alignment == "left":
                    xt = thisx
                else:
                    xt = thisx+dx+dxTextSpace
                yd = thisy+dy*0.5+dividerOffsY - (max(deltay,leadingMove)+yGap)
                self.colEndCallout(self, g, thisx, xt, yd, jOffs[-1], jOffs[-1]+dx+dxTextSpace)

            if i%columnMaximum==lim:
                if variColumn:
                    thisx += jOffs[-1]+xW
                else:
                    thisx = thisx+deltax
                thisy = upperlefty
            else:
                thisy = thisy-max(deltay,leadingMove)-yGap

        return g

    def demo(self):
        "Make sample legend."

        d = Drawing(200, 100)

        legend = Legend()
        legend.alignment = 'left'
        legend.x = 0
        legend.y = 100
        legend.dxTextSpace = 5
        items = 'red green blue yellow pink black white'.split()
        items = map(lambda i:(getattr(colors, i), i), items)
        legend.colorNamePairs = items

        d.add(legend, 'legend')

        return d

class TotalAnnotator(LegendColEndCallout):
    def __init__(self, lText='Total', rText='0.0', fontName='Times-Roman', fontSize=10,
            fillColor=colors.black, strokeWidth=0.5, strokeColor=colors.black, strokeDashArray=None,
            dx=0, dy=0, dly=0, dlx=(0,0)):
        self.lText = lText
        self.rText = rText
        self.fontName = fontName
        self.fontSize = fontSize
        self.fillColor = fillColor
        self.dy = dy
        self.dx = dx
        self.dly = dly
        self.dlx = dlx
        self.strokeWidth = strokeWidth
        self.strokeColor = strokeColor
        self.strokeDashArray = strokeDashArray

    def __call__(self,legend, g, x, xt, y, width, lWidth):
        from reportlab.graphics.shapes import String, Line
        fontSize = self.fontSize
        fontName = self.fontName
        fillColor = self.fillColor
        strokeColor = self.strokeColor
        strokeWidth = self.strokeWidth
        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize
        leading = fontSize*1.2
        yt = y+self.dy-ascent*1.3
        if self.lText and fillColor:
            g.add(String(xt,yt,self.lText,
                fontName=fontName,
                fontSize=fontSize,
                fillColor=fillColor,
                textAnchor = "start"))
        if self.rText:
            g.add(String(xt+width,yt,self.rText,
                fontName=fontName,
                fontSize=fontSize,
                fillColor=fillColor,
                textAnchor = "end"))
        if strokeWidth and strokeColor:
            yL = y+self.dly-leading
            g.add(Line(x+self.dlx[0],yL,x+self.dlx[1]+lWidth,yL,
                    strokeColor=strokeColor, strokeWidth=strokeWidth,
                    strokeDashArray=self.strokeDashArray))

class LineSwatch(Widget):
    """basically a Line with properties added so it can be used in a LineLegend"""
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x-coordinate for swatch line start point"),
        y = AttrMapValue(isNumber, desc="y-coordinate for swatch line start point"),
        width = AttrMapValue(isNumber, desc="length of swatch line"),
        height = AttrMapValue(isNumber, desc="used for line strokeWidth"),
        strokeColor = AttrMapValue(isColorOrNone, desc="color of swatch line"),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc="dash array for swatch line"),
    )

    def __init__(self):
        from reportlab.lib.colors import red
        from reportlab.graphics.shapes import Line
        self.x = 0
        self.y = 0
        self.width  = 20
        self.height = 1
        self.strokeColor = red
        self.strokeDashArray = None

    def draw(self):
        l = Line(self.x,self.y,self.x+self.width,self.y)
        l.strokeColor = self.strokeColor
        l.strokeDashArray  = self.strokeDashArray
        l.strokeWidth = self.height
        return l

class LineLegend(Legend):
    """A subclass of Legend for drawing legends with lines as the
    swatches rather than rectangles. Useful for lineCharts and
    linePlots. Should be similar in all other ways the the standard
    Legend class.
    """

    def __init__(self):
        Legend.__init__(self)

        # Size of swatch rectangle.
        self.dx = 10
        self.dy = 2

    def _defaultSwatch(self,x,thisy,dx,dy,fillColor,strokeWidth,strokeColor):
        l =  LineSwatch()
        l.x = x
        l.y = thisy
        l.width = dx
        l.height = dy
        l.strokeColor = fillColor
        return l

def sample1c():
    "Make sample legend."

    d = Drawing(200, 100)

    legend = Legend()
    legend.alignment = 'right'
    legend.x = 0
    legend.y = 100
    legend.dxTextSpace = 5
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items

    d.add(legend, 'legend')

    return d


def sample2c():
    "Make sample legend."

    d = Drawing(200, 100)

    legend = Legend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items

    d.add(legend, 'legend')

    return d

def sample3():
    "Make sample legend with line swatches."

    d = Drawing(200, 100)

    legend = LineLegend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items
    d.add(legend, 'legend')

    return d


def sample3a():
    "Make sample legend with line swatches and dasharrays on the lines."

    d = Drawing(200, 100)

    legend = LineLegend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    darrays = ([2,1], [2,5], [2,2,5,5], [1,2,3,4], [4,2,3,4], [1,2,3,4,5,6], [1])
    cnp = []
    for i in range(0, len(items)):
        l =  LineSwatch()
        l.strokeColor = getattr(colors, items[i])
        l.strokeDashArray = darrays[i]
        cnp.append((l, items[i]))
    legend.colorNamePairs = cnp
    d.add(legend, 'legend')

    return d
