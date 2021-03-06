# -*- test-case-name: axiom.test.test_upgrading -*-
from twisted.trial import unittest

from axiom import store, upgrade, item, errors

from twisted.application.service import IService

def axiomInvalidate(itemClass):
    """
    Remove the registered item class from the Axiom module system's memory,
    including: the item's current schema, legacy schema declarations, and
    upgraders.

    This makes it possible, for example, to reload a module without Axiom
    complaining about it.

    This API is still in a test module because it is _NOT YET SAFE_ for using
    while databases are open; it does not interact with open databases' caches,
    for example.

    @param itemClass: an Item subclass that you no longer wish to use.
    """
    store._typeNameToMostRecentClass.pop(itemClass.typeName, None)

    for (tnam, schever) in item._legacyTypes.keys():
        if tnam == itemClass.typeName:
            item._legacyTypes.pop((tnam, schever))

    for k in upgrade._upgradeRegistry.keys():
        if k[0] == itemClass.typeName:
            upgrade._upgradeRegistry.pop(k)

def axiomInvalidateModule(moduleObject):
    """
    Call L{axiomInvalidate} on all Item subclasses defined in a module.
    """
    for v in moduleObject.__dict__.values():
        if isinstance(v, item.MetaItem):
            axiomInvalidate(v)

from axiom.test import oldapp

axiomInvalidateModule(oldapp)

from axiom.test import toonewapp

axiomInvalidateModule(toonewapp)

from axiom.test import morenewapp

axiomInvalidateModule(morenewapp)

from axiom.test import newapp

from axiom.test import oldpath

axiomInvalidateModule(oldpath)

from axiom.test import newpath

axiomInvalidateModule(newpath)


def choose(module=None):
    """
    Choose among the various "adventurer" modules for upgrade tests.

    @param module: the module object which should next be treated as "current".
    """

    axiomInvalidateModule(oldapp)
    axiomInvalidateModule(toonewapp)
    axiomInvalidateModule(morenewapp)
    axiomInvalidateModule(newapp)

    if module is not None:
        reload(module)

class SchemaUpgradeTest(unittest.TestCase):
    def setUp(self):
        self.dbdir = self.mktemp()

    def openStore(self, dbg=False):
        self.currentStore = store.Store(self.dbdir, debug=dbg)
        return self.currentStore

    def closeStore(self):
        self.currentStore.close()
        self.currentStore = None

    def startStoreService(self):
        svc = IService(self.currentStore)
        svc.getServiceNamed("Batch Processing Controller").disownServiceParent()
        svc.startService()


class SwordUpgradeTest(SchemaUpgradeTest):

    def tearDown(self):
        choose(oldapp)

    def testUnUpgradeableStore(self):
        self._testTwoObjectUpgrade()
        choose(toonewapp)
        self.assertRaises(errors.NoUpgradePathAvailable, self.openStore)

    def testUpgradeWithMissingVersion(self):
        playerID, swordID = self._testTwoObjectUpgrade()
        choose(morenewapp)
        s = self.openStore()
        self.startStoreService()
        def afterUpgrade(result):
            player = s.getItemByID(playerID, autoUpgrade=False)
            sword = s.getItemByID(swordID, autoUpgrade=False)
            self._testPlayerAndSwordState(player, sword)
        return s.whenFullyUpgraded().addCallback(afterUpgrade)

    def _testTwoObjectUpgrade(self):
        choose(oldapp)
        s = self.openStore()
        self.assertIdentical(
            store._typeNameToMostRecentClass[oldapp.Player.typeName],
            oldapp.Player)

        sword = oldapp.Sword(
            store=s,
            name=u'flaming vorpal doom',
            hurtfulness=7
            )

        player = oldapp.Player(
            store=s,
            name=u'Milton',
            sword=sword
            )

        self.closeStore()

        # Perform an adjustment.

        return player.storeID, sword.storeID

    def testTwoObjectUpgrade_OuterFirst(self):
        playerID, swordID = self._testTwoObjectUpgrade()
        player, sword = self._testLoadPlayerFirst(playerID, swordID)
        self._testPlayerAndSwordState(player, sword)

    def testTwoObjectUpgrade_InnerFirst(self):
        playerID, swordID = self._testTwoObjectUpgrade()
        player, sword = self._testLoadSwordFirst(playerID, swordID)
        self._testPlayerAndSwordState(player, sword)

    def testTwoObjectUpgrade_AutoOrder(self):
        playerID, swordID = self._testTwoObjectUpgrade()
        player, sword = self._testAutoUpgrade(playerID, swordID)
        self._testPlayerAndSwordState(player, sword)

    def testTwoObjectUpgrade_UseService(self):
        playerID, swordID = self._testTwoObjectUpgrade()
        choose(newapp)
        s = self.openStore()
        self.startStoreService()

        # XXX *this* test really needs 10 or so objects to play with in order
        # to be really valid...

        def afterUpgrade(result):
            player = s.getItemByID(playerID, autoUpgrade=False)
            sword = s.getItemByID(swordID, autoUpgrade=False)
            self._testPlayerAndSwordState(player, sword)

        return s.whenFullyUpgraded().addCallback(afterUpgrade)

    def _testAutoUpgrade(self, playerID, swordID):
        choose(newapp)
        s = self.openStore()

        # XXX: this is certainly not the right API, but I needed a white-box
        # test before I started messing around with starting processes or
        # scheduling tasks automatically.
        while s._upgradeOneThing():
            pass

        player = s.getItemByID(playerID, autoUpgrade=False)
        sword = s.getItemByID(swordID, autoUpgrade=False)

        return player, sword

    def _testLoadPlayerFirst(self, playerID, swordID):
        # Everything old is new again
        choose(newapp)

        s = self.openStore()
        player = s.getItemByID(playerID)
        sword = s.getItemByID(swordID)
        return player, sword

    def _testLoadSwordFirst(self, playerID, swordID):
        choose(newapp)

        s = self.openStore()
        sword = s.getItemByID(swordID)
        player = s.getItemByID(playerID)
        return player, sword

    def _testPlayerAndSwordState(self, player, sword):
        assert not player.__legacy__
        assert not sword.__legacy__
        self.assertEquals(player.name, 'Milton')
        self.failIf(hasattr(player, 'sword'))
        self.assertEquals(sword.name, 'flaming vorpal doom')
        self.assertEquals(sword.damagePerHit, 14)
        self.failIf(hasattr(sword, 'hurtfulness'))
        self.assertEquals(sword.owner.storeID, player.storeID)
        self.assertEquals(type(sword.owner), type(player))
        self.assertEquals(sword.owner, player)
        self.assertEquals(sword.activated, 1)
        self.assertEquals(player.activated, 1)


from axiom.substore import SubStore

class SubStoreCompat(SwordUpgradeTest):
    def setUp(self):
        self.topdbdir = self.mktemp()
        self.subStoreID = None

    def openStore(self):
        self.currentTopStore = store.Store(self.topdbdir)
        if self.subStoreID is not None:
            self.currentSubStore = self.currentTopStore.getItemByID(self.subStoreID).open()
        else:
            ss = SubStore.createNew(self.currentTopStore,
                                    ['sub'])
            self.subStoreID = ss.storeID
            self.currentSubStore = ss.open()
        return self.currentSubStore

    def closeStore(self):
        self.currentSubStore.close()
        self.currentTopStore.close()
        self.currentSubStore = None
        self.currentTopStore = None

    def startStoreService(self):
        svc = IService(self.currentTopStore)
        svc.getServiceNamed("Batch Processing Controller").disownServiceParent()
        svc.startService()

class PathUpgrade(SchemaUpgradeTest):
    def testUpgradePath(self):
        """
        Verify that you can upgrade a path attribute in the simplest possible
        way.
        """
        axiomInvalidateModule(newpath)
        reload(oldpath)
        self.openStore()
        nfp = self.currentStore.newFilePath("pathname")
        oldpath.Path(store=self.currentStore,
                     thePath=nfp)
        self.closeStore()
        axiomInvalidateModule(oldpath)
        reload(newpath)
        self.openStore()
        def checkPathEquivalence(n):
            self.assertEquals(
                self.currentStore.findUnique(newpath.Path).thePath.path,
                nfp.path)
        self.startStoreService()
        return self.currentStore.whenFullyUpgraded().addCallback(
            checkPathEquivalence)


from axiom.test import oldcirc
axiomInvalidateModule(oldcirc)
from axiom.test import newcirc
axiomInvalidateModule(newcirc)


from axiom.test import oldobsolete
axiomInvalidateModule(oldobsolete)

from axiom.test import newobsolete
axiomInvalidateModule(newobsolete)

from zope.interface import Interface

class IObsolete(Interface):
    """
    Interface representing an undesirable feature.
    """

class DeletionTest(SchemaUpgradeTest):
    def testCircular(self):
        """
        If you access an item, B, through a reference on another item, A, which
        is deleted in the course of B's upgrade, you should still get a
        reference to B.
        """
        reload(oldcirc)
        self.openStore()
        b = oldcirc.B(a=oldcirc.A(store=self.currentStore),
                      store=self.currentStore)
        b.a.b = b

        self.closeStore()

        axiomInvalidateModule(oldcirc)
        reload(newcirc)

        self.openStore()
        origA = self.currentStore.findUnique(newcirc.A)
        origB = origA.b
        secondA = self.currentStore.findUnique(newcirc.A)
        secondB = secondA.b
        self.assertEquals(origB, secondB)
        self.assertNotEqual(origA, secondA)

    def testPowerupsFor(self):
        """
        Powerups deleted during upgrades should be omitted from the results of
        powerupsFor.
        """
        reload(oldobsolete)
        self.openStore()
        o = oldobsolete.Obsolete(store=self.currentStore)
        self.currentStore.powerUp(o, IObsolete)
        # sanity check
        self.assertEquals(IObsolete(self.currentStore), o)
        self.closeStore()

        axiomInvalidateModule(oldobsolete)
        reload(newobsolete)
        self.openStore()
        self.assertEquals(list(self.currentStore.powerupsFor(IObsolete)), [])
        self.closeStore()
        axiomInvalidateModule(newobsolete)

    def testPowerupsAdapt(self):
        """
        Powerups deleted during upgrades should be omitted from the results of
        powerupsFor.
        """
        reload(oldobsolete)
        self.openStore()
        o = oldobsolete.Obsolete(store=self.currentStore)
        self.currentStore.powerUp(o, IObsolete)
        # sanity check
        self.assertEquals(IObsolete(self.currentStore), o)
        self.closeStore()

        axiomInvalidateModule(oldobsolete)
        reload(newobsolete)
        self.openStore()
        self.assertEquals(IObsolete(self.currentStore, None), None)
        self.closeStore()
        axiomInvalidateModule(newobsolete)
