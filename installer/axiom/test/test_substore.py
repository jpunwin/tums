
from twisted.application.service import Service, IService

from twisted.trial import unittest

from axiom.store import Store
from axiom.item import Item
from axiom.substore import SubStore

from axiom.attributes import text, bytes, boolean, inmemory



class SubStored(Item):

    schemaVersion = 1
    typeName = 'substoredthing'
    a = text()
    b = bytes()


class YouCantStartThis(Item, Service):

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    started = boolean(default=False)

    def startService(self):
        self.started = True

class YouShouldStartThis(Item, Service):

    parent = inmemory()
    running = inmemory()
    name = inmemory()

    started = boolean(default=False)

    def startService(self):
        self.started = True


class SubStoreTest(unittest.TestCase):

    def testOneThing(self):
        topdb = self.mktemp()
        s = Store(topdb)
        ss = SubStore.createNew(s, ['account', 'bob@divmod.com'])
        s2 = ss.open()

        ssd = SubStored(store=s2, a=u'hello world', b='what, its text')
        oid = ss.storeID
        oid2 = ssd.storeID

        s2.close()
        s.close()

        reopens = Store(topdb)
        reopenss = reopens.getItemByID(oid)
        reopens2 = reopenss.open()
        reopenssd = reopens2.getItemByID(oid2)

        self.assertEquals(reopenssd.a, u'hello world')
        self.assertEquals(reopenssd.b, 'what, its text')


class SubStoreStartupSemantics(unittest.TestCase):
    """
    These tests verify that interactions between store and substore services
    are correct.  They also provide some documentation of expected edge-case
    behavior.  Read the code if you are interested in how to get startup
    notifications from substore items.
    """

    def setUp(self):
        """
        Set up the tests by creating a store and a substore and opening them both.
        """
        self.topdb = topdb = Store(self.mktemp())
        self.ssitem = ssitem = SubStore.createNew(
            topdb, ["dontstartme", "really"])
        self.ss = ssitem.open()
        self.serviceStarted = False

    def testDontStartNormally(self):
        """
        Substores' services are not supposed to be started when their parent stores
        are.
        """
        ss = self.ss
        ycst = YouCantStartThis(store=ss)
        ss.powerUp(ycst, IService)
        self._startService()
        self.failIf(ycst.started)

    def testStartEverythingExplicitly(self):
        """
        Substores implement IService themselves, just as regular stores do, via
        the special-case machinery.
        """
        ss = self.ss
        ysst = YouShouldStartThis(store=ss)
        ss.powerUp(ysst, IService)
        self.topdb.powerUp(self.ssitem, IService)
        self._startService()
        self.failUnless(ysst.started)

    def _startService(self):
        """
        Start the service and make sure we know it's started so tearDown can
        shut it down.
        """
        assert not self.serviceStarted
        self.serviceStarted = True
        return IService(self.topdb).startService()

    def tearDown(self):
        """
        Stop services that may have been started by these test cases.
        """
        if self.serviceStarted:
            return IService(self.topdb).stopService()
