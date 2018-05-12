YAHOO.util.Dom=function(){var ua=navigator.userAgent.toLowerCase();var isOpera=(ua.indexOf('opera')!=-1);var isIE=(ua.indexOf('msie')!=-1&&!isOpera);var id_counter=0;return{get:function(el){if(typeof el!='string'&&!(el instanceof Array)){return el;}if(typeof el=='string'){return document.getElementById(el);}else{var collection=[];for(var i=0,len=el.length;i<len;++i){collection[collection.length]=this.get(el[i]);}return collection;}return null;},getStyle:function(el,property){var f=function(el){var value=null;var dv=document.defaultView;if(property=='opacity'&&el.filters){value=1;try{value=el.filters.item('DXImageTransform.Microsoft.Alpha').opacity/100;}catch(e){try{value=el.filters.item('alpha').opacity/100;}catch(e){}}}else if(el.style[property]){value=el.style[property];}else if(el.currentStyle&&el.currentStyle[property]){value=el.currentStyle[property];}else if(dv&&dv.getComputedStyle){var converted='';for(var i=0,len=property.length;i<len;++i){if(property.charAt(i)==property.charAt(i).toUpperCase()){converted=converted+'-'+property.charAt(i).toLowerCase();}else{converted=converted+property.charAt(i);}}if(dv.getComputedStyle(el,'')&&dv.getComputedStyle(el,'').getPropertyValue(converted)){value=dv.getComputedStyle(el,'').getPropertyValue(converted);}}return value;};return this.batch(el,f,this,true);},setStyle:function(el,property,val){var f=function(el){switch(property){case'opacity':if(isIE&&typeof el.style.filter=='string'){el.style.filter='alpha(opacity='+val*100+')';if(!el.currentStyle||!el.currentStyle.hasLayout){el.style.zoom=1;}}else{el.style.opacity=val;el.style['-moz-opacity']=val;el.style['-khtml-opacity']=val;}break;default:el.style[property]=val;}};this.batch(el,f,this,true);},getXY:function(el){var f=function(el){if(el.parentNode===null||this.getStyle(el,'display')=='none'){return false;}var parent=null;var pos=[];var box;if(el.getBoundingClientRect){box=el.getBoundingClientRect();var scrollTop=Math.max(document.documentElement.scrollTop,document.body.scrollTop);var scrollLeft=Math.max(document.documentElement.scrollLeft,document.body.scrollLeft);return[box.left+scrollLeft,box.top+scrollTop];}else if(document.getBoxObjectFor){box=document.getBoxObjectFor(el);var borderLeft=parseInt(this.getStyle(el,'borderLeftWidth'));var borderTop=parseInt(this.getStyle(el,'borderTopWidth'));pos=[box.x-borderLeft,box.y-borderTop];}else{pos=[el.offsetLeft,el.offsetTop];parent=el.offsetParent;if(parent!=el){while(parent){pos[0]+=parent.offsetLeft;pos[1]+=parent.offsetTop;parent=parent.offsetParent;}}if(ua.indexOf('opera')!=-1||(ua.indexOf('safari')!=-1&&this.getStyle(el,'position')=='absolute')){pos[0]-=document.body.offsetLeft;pos[1]-=document.body.offsetTop;}}if(el.parentNode){parent=el.parentNode;}else{parent=null;}while(parent&&parent.tagName!='BODY'&&parent.tagName!='HTML'){pos[0]-=parent.scrollLeft;pos[1]-=parent.scrollTop;if(parent.parentNode){parent=parent.parentNode;}else{parent=null;}}return pos;};return this.batch(el,f,this,true);},getX:function(el){return this.getXY(el)[0];},getY:function(el){return this.getXY(el)[1];},setXY:function(el,pos,noRetry){var f=function(el){var style_pos=this.getStyle(el,'position');if(style_pos=='static'){this.setStyle(el,'position','relative');style_pos='relative';}var pageXY=YAHOO.util.Dom.getXY(el);if(pageXY===false){return false;}var delta=[parseInt(YAHOO.util.Dom.getStyle(el,'left'),10),parseInt(YAHOO.util.Dom.getStyle(el,'top'),10)];if(isNaN(delta[0])){delta[0]=(style_pos=='relative')?0:el.offsetLeft;}if(isNaN(delta[1])){delta[1]=(style_pos=='relative')?0:el.offsetTop;}if(pos[0]!==null){el.style.left=pos[0]-pageXY[0]+delta[0]+'px';}if(pos[1]!==null){el.style.top=pos[1]-pageXY[1]+delta[1]+'px';}var newXY=this.getXY(el);if(!noRetry&&(newXY[0]!=pos[0]||newXY[1]!=pos[1])){var retry=function(){YAHOO.util.Dom.setXY(el,pos,true);};setTimeout(retry,0);}};this.batch(el,f,this,true);},setX:function(el,x){this.setXY(el,[x,null]);},setY:function(el,y){this.setXY(el,[null,y]);},getRegion:function(el){var f=function(el){return new YAHOO.util.Region.getRegion(el);};return this.batch(el,f,this,true);},getClientWidth:function(){return this.getViewportWidth();},getClientHeight:function(){return this.getViewportHeight();},getElementsByClassName:function(className,tag,root){var re=new RegExp('(?:^|\\s+)'+className+'(?:\\s+|$)');var method=function(el){return re.test(el['className']);};return this.getElementsBy(method,tag,root);},hasClass:function(el,className){var f=function(el){var re=new RegExp('(?:^|\\s+)'+className+'(?:\\s+|$)');return re.test(el['className']);};return this.batch(el,f,this,true);},addClass:function(el,className){var f=function(el){if(this.hasClass(el,className)){return;}el['className']=[el['className'],className].join(' ');};this.batch(el,f,this,true);},removeClass:function(el,className){var f=function(el){if(!this.hasClass(el,className)){return;}var re=new RegExp('(?:^|\\s+)'+className+'(?:\\s+|$)','g');var c=el['className'];el['className']=c.replace(re,' ');};this.batch(el,f,this,true);},replaceClass:function(el,oldClassName,newClassName){var f=function(el){this.removeClass(el,oldClassName);this.addClass(el,newClassName);};this.batch(el,f,this,true);},generateId:function(el,prefix){prefix=prefix||'yui-gen';var f=function(el){el=el||{};if(!el.id){el.id=prefix+id_counter++;}return el.id;};return this.batch(el,f,this,true);},isAncestor:function(haystack,needle){haystack=this.get(haystack);if(!haystack||!needle){return false;}var f=function(needle){if(haystack.contains&&ua.indexOf('safari')<0){return haystack.contains(needle);}else if(haystack.compareDocumentPosition){return!!(haystack.compareDocumentPosition(needle)&16);}else{var parent=needle.parentNode;while(parent){if(parent==haystack){return true;}else if(parent.tagName=='HTML'){return false;}parent=parent.parentNode;}return false;}};return this.batch(needle,f,this,true);},inDocument:function(el){var f=function(el){return this.isAncestor(document.documentElement,el);};return this.batch(el,f,this,true);},getElementsBy:function(method,tag,root){tag=tag||'*';root=this.get(root)||document;var nodes=[];var elements=root.getElementsByTagName(tag);if(!elements.length&&(tag=='*'&&root.all)){elements=root.all;}for(var i=0,len=elements.length;i<len;++i){if(method(elements[i])){nodes[nodes.length]=elements[i];}}return nodes;},batch:function(el,method,o,override){el=this.get(el);var scope=(override)?o:window;if(!el||el.tagName||!el.length){return method.call(scope,el,o);}var collection=[];for(var i=0,len=el.length;i<len;++i){collection[collection.length]=method.call(scope,el[i],o);}return collection;},getDocumentHeight:function(){var scrollHeight=-1,windowHeight=-1,bodyHeight=-1;var marginTop=parseInt(this.getStyle(document.body,'marginTop'),10);var marginBottom=parseInt(this.getStyle(document.body,'marginBottom'),10);var mode=document.compatMode;if((mode||isIE)&&!isOpera){switch(mode){case'CSS1Compat':scrollHeight=((window.innerHeight&&window.scrollMaxY)?window.innerHeight+window.scrollMaxY:-1);windowHeight=[document.documentElement.clientHeight,self.innerHeight||-1].sort(function(a,b){return(a-b);})[1];bodyHeight=document.body.offsetHeight+marginTop+marginBottom;break;default:scrollHeight=document.body.scrollHeight;bodyHeight=document.body.clientHeight;}}else{scrollHeight=document.documentElement.scrollHeight;windowHeight=self.innerHeight;bodyHeight=document.documentElement.clientHeight;}var h=[scrollHeight,windowHeight,bodyHeight].sort(function(a,b){return(a-b);});return h[2];},getDocumentWidth:function(){var docWidth=-1,bodyWidth=-1,winWidth=-1;var marginRight=parseInt(this.getStyle(document.body,'marginRight'),10);var marginLeft=parseInt(this.getStyle(document.body,'marginLeft'),10);var mode=document.compatMode;if(mode||isIE){switch(mode){case'CSS1Compat':docWidth=document.documentElement.clientWidth;bodyWidth=document.body.offsetWidth+marginLeft+marginRight;winWidth=self.innerWidth||-1;break;default:bodyWidth=document.body.clientWidth;winWidth=document.body.scrollWidth;break;}}else{docWidth=document.documentElement.clientWidth;bodyWidth=document.body.offsetWidth+marginLeft+marginRight;winWidth=self.innerWidth;}var w=[docWidth,bodyWidth,winWidth].sort(function(a,b){return(a-b);});return w[2];},getViewportHeight:function(){var height=-1;var mode=document.compatMode;if((mode||isIE)&&!isOpera){switch(mode){case'CSS1Compat':height=document.documentElement.clientHeight;break;default:height=document.body.clientHeight;}}else{height=self.innerHeight;}return height;},getViewportWidth:function(){var width=-1;var mode=document.compatMode;if(mode||isIE){switch(mode){case'CSS1Compat':width=document.documentElement.clientWidth;break;default:width=document.body.clientWidth;}}else{width=self.innerWidth;}return width;}};}();YAHOO.util.Region=function(t,r,b,l){this.top=t;this[1]=t;this.right=r;this.bottom=b;this.left=l;this[0]=l;};YAHOO.util.Region.prototype.contains=function(region){return(region.left>=this.left&&region.right<=this.right&&region.top>=this.top&&region.bottom<=this.bottom);};YAHOO.util.Region.prototype.getArea=function(){return((this.bottom-this.top)*(this.right-this.left));};YAHOO.util.Region.prototype.intersect=function(region){var t=Math.max(this.top,region.top);var r=Math.min(this.right,region.right);var b=Math.min(this.bottom,region.bottom);var l=Math.max(this.left,region.left);if(b>=t&&r>=l){return new YAHOO.util.Region(t,r,b,l);}else{return null;}};YAHOO.util.Region.prototype.union=function(region){var t=Math.min(this.top,region.top);var r=Math.max(this.right,region.right);var b=Math.max(this.bottom,region.bottom);var l=Math.min(this.left,region.left);return new YAHOO.util.Region(t,r,b,l);};YAHOO.util.Region.prototype.toString=function(){return("Region {"+"t: "+this.top+", r: "+this.right+", b: "+this.bottom+", l: "+this.left+"}");};YAHOO.util.Region.getRegion=function(el){var p=YAHOO.util.Dom.getXY(el);var t=p[1];var r=p[0]+el.offsetWidth;var b=p[1]+el.offsetHeight;var l=p[0];return new YAHOO.util.Region(t,r,b,l);};YAHOO.util.Point=function(x,y){this.x=x;this.y=y;this.top=y;this[1]=y;this.right=x;this.bottom=y;this.left=x;this[0]=x;};YAHOO.util.Point.prototype=new YAHOO.util.Region();
