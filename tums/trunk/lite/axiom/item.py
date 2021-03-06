# -*- test-case-name: axiom.test -*-

__metaclass__ = type

from zope.interface import implements

from inspect import getabsfile

from twisted.python import log
from twisted.python.reflect import qual, namedAny
from twisted.python.util import unsignedID
from twisted.python.util import mergeFunctionMetadata
from twisted.application.service import IService, IServiceCollection, MultiService

from axiom import slotmachine, _schema, iaxiom

from axiom.iaxiom import IColumn, IPowerupIndirector

from axiom.attributes import (
    SQLAttribute, _ComparisonOperatorMuxer, _MatchingOperationMuxer,
    _OrderingMixin, _ContainableMixin, Comparable, compare, inmemory,
    reference, text, integer, AND, _cascadingDeletes)

_typeNameToMostRecentClass = {}

def normalize(qualName):
    """
    Turn a fully-qualified Python name into a string usable as part of a
    table name.
    """
    return qualName.lower().replace('.', '_')

class NoInheritance(RuntimeError):
    """
    Inheritance is as-yet unsupported by XAtop.
    """

class NotInStore(RuntimeError):
    """
    """

class CantInstantiateItem(RuntimeError):
    """You can't instantiate Item directly.  Make a subclass.
    """

class MetaItem(slotmachine.SchemaMetaMachine):
    """Simple metaclass for Item that adds Item (and its subclasses) to
    _typeNameToMostRecentClass mapping.
    """

    def __new__(meta, name, bases, dictionary):
        T = slotmachine.SchemaMetaMachine.__new__(meta, name, bases, dictionary)
        if T.__name__ == 'Item' and T.__module__ == __name__:
            return T
        T.__already_inherited__ += 1
        if T.__already_inherited__ >= 2:
            raise NoInheritance("already inherited from item once: "
                                "in-database inheritance not yet supported")
        if T.typeName is None:
            T.typeName = normalize(qual(T))
        if T.schemaVersion is None:
            T.schemaVersion = 1
        if T.typeName in _typeNameToMostRecentClass:
            if T.__legacy__:
                return T
            otherT = _typeNameToMostRecentClass[T.typeName]

            if (otherT.__name__ == T.__name__
                    and getabsfile(T) == getabsfile(otherT)
                    and T.__module__ != otherT.__module__):

                if len(T.__module__) < len(otherT.__module__):
                    relmod = T.__module__
                else:
                    relmod = otherT.__module__

                raise RuntimeError("Use absolute imports; relative import"
                        " detected for type %r (imported from %r)" % (T.typeName, relmod))

            raise RuntimeError("2 definitions of axiom typename %r: %r %r" % (
                    T.typeName, T, _typeNameToMostRecentClass[T.typeName]))
        _typeNameToMostRecentClass[T.typeName] = T
        return T


    def __cmp__(self, other):
        """
        Ensure stable sorting between Item classes.  This provides determinism
        in SQL generation, which is beneficial for debugging and performance
        purposes.
        """
        if isinstance(other, MetaItem):
            return cmp(self.typeName, other.typeName)
        return NotImplemented


def noop():
    pass

class _StoreIDComparer(Comparable):
    """
    See Comparable's docstring for the explanation of the requirements of my implementation.
    """
    implements(IColumn)

    def __init__(self, type):
        self.type = type

    # attributes required by ColumnComparer
    def infilter(self, pyval, oself, store):
        return pyval

    def outfilter(self, dbval, oself):
        return dbval

    def getShortColumnName(self, store):
        return store.getShortColumnName(self)

    def getColumnName(self, store):
        return store.getColumnName(self)


class _SpecialStoreIDAttribute(slotmachine.SetOnce):
    """
    Because storeID is special (it's unique, it determines a row's cache
    identity, it's immutable, etc) we don't use a regular SQLAttribute to
    represent it - but it still needs to be compared with other SQL attributes,
    as it is in fact represented by the 'oid' database column.

    I implement set-once semantics to enforce immutability, but delegate
    comparison operations to _StoreIDComparer.
    """
    def __get__(self, oself, type=None):
        if type is not None and oself is None:
            if type._storeIDComparer is None:
                # Reuse the same instance so that the store can use it
                # as a key for various caching, like any other attributes.
                type._storeIDComparer = _StoreIDComparer(type)
            return type._storeIDComparer
        return super(_SpecialStoreIDAttribute, self).__get__(oself, type)


def serviceSpecialCase(item, pups):
    if item._axiom_service is not None:
        return item._axiom_service
    svc = MultiService()
    for subsvc in pups:
        subsvc.setServiceParent(svc)
    item._axiom_service = svc
    return svc



class InstallableMixin(object):
    """
    Mixin for Items which can be installed as powerups on other Items
    and which must keep track of which item they are installed on.

    If a classes mixing this in defines named C{installedOn}, it will
    be bound to the object which is the target of the install.
    """
    def installOn(self, other):
        if hasattr(self, 'installedOn'):
            assert self.installedOn is None or self.installedOn is other, (
                "Cannot install %r on more than one thing (was installed on "
                "%r, tried to install on %r)" % (self.__class__, self.installedOn, other))
            self.installedOn = other


class Empowered(object):

    aggregateInterfaces = {
        IService: serviceSpecialCase,
        IServiceCollection: serviceSpecialCase}

    def powerUp(self, powerup, interface, priority=0):
        """
        Installs a powerup (e.g. plugin) on an item or store.

        Powerups will be returned in an iterator when queried for using the
        'powerupsFor' method.  Normally they will be returned in order of
        installation [this may change in future versions, so please don't
        depend on it].  Higher priorities are returned first.  If you have
        something that should run before "normal" powerups, pass
        POWERUP_BEFORE; if you have something that should run after, pass
        POWERUP_AFTER.  We suggest not depending too heavily on order of
        execution of your powerups, but if finer-grained control is necessary
        you may pass any integer.  Normal (unspecified) priority is zero.

        Powerups will only be installed once on a given item.  If you install a
        powerup for a given interface with priority 1, then again with priority
        30, the powerup will be adjusted to priority 30 but future calls to
        powerupFor will still only return that powerup once.

        @param powerup: an Item that implements C{interface}
        @param interface: a zope interface

        @param priority: An int; preferably either POWERUP_BEFORE,
        POWERUP_AFTER, or unspecified.

        @raise TypeError: raises if interface is IPowerupIndirector You may not
        install a powerup for IPowerupIndirector because that would be
        nonsensical.
        """
        if interface is IPowerupIndirector:
            raise TypeError(
                "You cannot install a powerup for IPowerupIndirector: " +
                powerup)

        forc = self.store.findOrCreate(_PowerupConnector,
                                       item=self,
                                       interface=unicode(qual(interface)),
                                       powerup=powerup)
        forc.priority = priority


    def powerDown(self, powerup, interface):
        """
        Remove a powerup.
        """
        for cable in self.store.query(_PowerupConnector,
                                      AND(_PowerupConnector.item == self,
                                          _PowerupConnector.interface == unicode(qual(interface)),
                                          _PowerupConnector.powerup == powerup)):
            cable.deleteFromStore()
            return
        raise ValueError("Not powered up for %r with %r" % (interface, powerup))


    def __conform__(self, interface):
        """
        For 'normal' interfaces, returns the first powerup found when doing
        self.powerupsFor(interface).

        Certain interfaces are special - IService from twisted.application
        being the main special case - and will be aggregated according to
        special rules.  The full list of such interfaces is present in the
        'aggregateInterfaces' class attribute.
        """
        if (self.store is None  # Don't bother doing a *query* if we're not
                                # even stored in a store yet
            or interface is IPowerupIndirector): # you can't do a query for
                                                 # IPowerupIndirector, that
                                                 # would just start an infinite
                                                 # loop.
            return
        pups = self.powerupsFor(interface)
        agg = self.aggregateInterfaces
        if interface in agg:
            return agg[interface](self, pups)
        for p in pups:
            return p

    def powerupsFor(self, interface):
        """
        Returns powerups installed using C{powerUp}, in order of descending
        priority.

        Powerups found to have been deleted, either during the course of this
        powerupsFor iteration, during an upgrader, or previously, will not be
        returned.
        """
        name = unicode(qual(interface), 'ascii')
        for cable in self.store.query(
            _PowerupConnector,
            AND(_PowerupConnector.interface == name,
                _PowerupConnector.item == self),
            sort=_PowerupConnector.priority.descending):
            pup = cable.powerup
            if pup is None:
                # this powerup was probably deleted during an upgrader.
                cable.deleteFromStore()
            else:
                indirector = IPowerupIndirector(pup, None)
                if indirector is not None:
                    yield indirector.indirect(interface)
                else:
                    yield pup

    def interfacesFor(self, powerup):
        pc = _PowerupConnector
        for iface in self.store.query(pc,
                                      AND(pc.item == self,
                                          pc.powerup == powerup)).getColumn('interface'):
            yield namedAny(iface)


def transacted(func):
    """
    Return a callable which will invoke C{func} in a transaction using the
    C{store} attribute of the first parameter passed to it.  Typically this is
    used to create Item methods which are automatically run in a transaction.

    The attributes of the returned callable will resemble those of C{func} as
    closely as L{twisted.python.util.mergeFunctionMetadata} can make them.
    """
    def transactionified(item, *a, **kw):
        return item.store.transact(func, item, *a, **kw)
    return mergeFunctionMetadata(func, transactionified)



class Item(Empowered, slotmachine._Strict):
    # Python-Special Attributes
    __metaclass__ = MetaItem

    # Axiom-Special Attributes
    __dirty__ = inmemory()
    __legacy__ = False

    __already_inherited__ = 0

    # Private attributes.
    __store = inmemory()        # underlying reference to the store.

    __everInserted = inmemory() # has this object ever been inserted into the
                                # database?

    __justCreated = inmemory()  # was this object just created, i.e. is there
                                # no committed database representation of it
                                # yet

    __deleting = inmemory()     # has this been marked for deletion at
                                # checkpoint

    __deletingObject = inmemory() # being marked for deletion at checkpoint,
                                  # are we also deleting the central object row
                                  # (True: as in an actual delete) or are we
                                  # simply deleting the data row (False: as in
                                  # part of an upgrade)

    storeID = _SpecialStoreIDAttribute(default=None)
    _storeIDComparer = None
    _axiom_service = inmemory()

    def _currentlyValidAsReferentFor(self, store):
        """
        Is this object currently valid as a reference?  Objects which will be
        deleted in this transaction, or objects which are not in the same store
        are not valid.  See attributes.reference.__get__.
        """
        if store is None:
            # If your store is None, you can refer to whoever you want.  I'm in
            # a store but it doesn't matter that you're not.
            return True
        if self.store is not store:
            return False
        if self.__deletingObject:
            return False
        return True
    # return (self.store is store and not self.__deletingObject)

    def _schemaPrepareInsert(self, store):
        """
        Prepare each attribute in my schema for insertion into a given store,
        either by upgrade or by creation.  This makes sure all references point
        to this store and all relative paths point to this store's files
        directory.
        """
        for name, atr in self.getSchema():
            atr.prepareInsert(self, store)

    def store():
        def get(self):
            return self.__store
        def set(self, store):
            if self.__store is not None:
                raise AttributeError(
                    "Store already set - can't move between stores")
            self._schemaPrepareInsert(store)
            self.__store = store
            oid = self.storeID = self.store.executeSchemaSQL(
                _schema.CREATE_OBJECT, [self.store.getTypeID(type(self))])
            store.objectCache.cache(oid, self)
            if store.autocommit:
                log.msg(interface=iaxiom.IStatEvent,
                        name='database', stat_autocommits=1)

                self.checkpoint()
            else:
                self.touch()
            self.activate()
            self.stored()
        return get, set, """

        A reference to a Store; when set for the first time, inserts this object
        into that store.  Cannot be set twice; once inserted, objects are
        'stuck' to a particular store and must be copied by creating a new
        Item.

        """

    store = property(*store())

# XXX: Think about how to do this _safely_ (e.g. not recursing infinitely
# through circular references) before turning it on
    def __repr__(self):
        L = [self.__name__]
        L.append('(')
        A = []
        for nam, atr in sorted(self.getSchema()):
            try:
                V = atr.reprFor(self)
            except:
                import traceback
                import sys
                traceback.print_exc(file=sys.stdout)
                V = "<error>"
            A.append('%s=%s' % (nam, V))
        A.append('storeID=' + str(self.storeID))
        L.append(', '.join(A))
        L.append(')')
        L.append('@0x%X' % unsignedID(self))
        return ''.join(L)


    def __subinit__(self, **kw):
        """
        Initializer called regardless of whether this object was created by
        instantiation or loading from the database.
        """
        self._axiom_service = None
        self.__dirty__ = {}
        to__store = kw.pop('__store', None)
        to__everInserted = kw.pop('__everInserted', False)
        to__justUpgraded = kw.pop('__justUpgraded', False)
        self.__store = to__store
        self.__everInserted = to__everInserted
        self.__deletingObject = False
        self.__deleting = False
        tostore = kw.pop('store',None)

        if not self.__everInserted:
            for (name, attr) in self.getSchema():
                if name not in kw:
                    kw[name] = attr.computeDefault()

        for k, v in kw.iteritems():
            setattr(self, k, v)

        if tostore != None:
            if to__justUpgraded:

                # we can't just set the store, because that allocates an ID.
                # we do still need to do all the attribute prep, make sure
                # references refer to this store, paths are adjusted to point
                # to this store's static offset, etc.

                self._schemaPrepareInsert(tostore)
                self.__store = tostore
                if tostore.autocommit:
                    self.checkpoint()
            else:
                self.store = tostore

    def __init__(self, **kw):
        """
        Create a new Item.  This is called on an item *only* when it is being created
        for the first time, not when it is loaded from the database.  The
        'activate()' hook is called every time an item is loaded from the
        database, as well as the first time that an item is inserted into the
        store.  This will be inside __init__ if you pass a 'store' keyword
        argument to an Item's constructor.

        This takes an arbitrary set of keyword arguments, which will be set as
        attributes on the created item.  Subclasses of Item must honor this
        signature.
        """
        if type(self) is Item:
            raise CantInstantiateItem()
        self.__justCreated = True
        self.__subinit__(**kw)

    def __finalizer__(self):
        return noop

    def existingInStore(cls, store, storeID, attrs):
        """Create and return a new instance from a row from the store."""
        self = cls.__new__(cls)

        self.__justCreated = False
        self.__subinit__(__store=store,
                         storeID=storeID,
                         __everInserted=True)

        schema = list(self.getSchema())
        assert len(schema) == len(attrs), "invalid number of attributes"
        for data, (name, attr) in zip(attrs, schema):
            attr.loaded(self, data)
        self.activate()
        return self
    existingInStore = classmethod(existingInStore)

    def activate(self):
        """The object was loaded from the store.
        """

    def getSchema(cls):
        """
        return all persistent class attributes
        """
        for name, atr in cls.__attributes__:
            atr = atr.__get__(None, cls)
            if isinstance(atr, SQLAttribute):
                yield (name, atr)

    getSchema = classmethod(getSchema)


    def persistentValues(self):
        """
        Return a dictionary of all attributes which will be/have been/are being
        stored in the database.
        """
        return dict((k, getattr(self, k)) for (k, attr) in self.getSchema())


    def touch(self):
        # xxx what
        if self.store is None or self.store.transaction is None:
            return
        self.store.transaction.add(self)

    def revert(self):
        if self.__justCreated:
            # The SQL revert has already been taken care of.
            if not self.__legacy__:
                self.store.objectCache.uncache(self.storeID, self)
            return
        self.__dirty__.clear()
        dbattrs = self.store.querySQL(
            self._baseSelectSQL(self.store),
            [self.storeID])[0]

        for data, (name, atr) in zip(dbattrs, self.getSchema()):
            atr.loaded(self, data)

        self.__deleting = False
        self.__deletingObject = False

    def deleted(self):
        """User-definable callback that is invoked when an object is well and truly
        gone from the database; the transaction which deleted it has been
        committed.
        """


    def stored(self):
        """
        User-definable callback that is invoked when an object is placed into a
        Store for the very first time.

        If an Item is created with a store, this will be invoked I{after}
        C{activate}.
        """


    def committed(self):
        """
        Called after the database is brought into a consistent state with this
        object.
        """
        if self.__deleting:
            self.deleted()
            if not self.__legacy__:
                self.store.objectCache.uncache(self.storeID, self)
            self.__store = None
        self.__justCreated = False

    def checkpoint(self):
        """ Update the database to reflect in-memory changes made to this item; for
        example, to make it show up in store.query() calls where it is now
        valid, but was not the last time it was persisted to the database.

        This is called automatically when in 'autocommit mode' (i.e. not in a
        transaction) and at the end of each transaction for every object that
        has been changed.
        """

        if self.store is None:
            raise NotInStore("You can't checkpoint %r: not in a store" % (self,))


        if self.__deleting:
            if not self.__everInserted:
                # don't issue duplicate SQL and crap; we were created, then
                # destroyed immediately.
                return
            self.store.executeSQL(self._baseDeleteSQL(self.store), [self.storeID])
            # re-using OIDs plays havoc with the cache, and with other things
            # as well.  We need to make sure that we leave a placeholder row at
            # the end of the table.
            if self.__deletingObject:
                # Mark this object as dead.
                self.store.executeSchemaSQL(_schema.CHANGE_TYPE,
                                            [-1, self.storeID])

                # Can't do this any more:
                # self.store.executeSchemaSQL(_schema.DELETE_OBJECT, [self.storeID])

                # TODO: need to measure the performance impact of this, then do
                # it to make sure things are in fact deleted:
                # self.store.executeSchemaSQL(_schema.APP_VACUUM)

            else:
                assert self.__legacy__

            # we're done...
            if self.store.autocommit:
                self.committed()
            return

        if self.__everInserted:
            # case 1: we've been inserted before, either previously in this
            # transaction or we were loaded from the db
            if not self.__dirty__:
                # we might have been checkpointed twice within the same
                # transaction; just don't do anything.
                return
            self.store.executeSQL(*self._updateSQL())
        else:
            # case 2: we are in the middle of creating the object, we've never
            # been inserted into the db before
            schemaAttrs = self.getSchema()

            insertArgs = [self.storeID]
            for (ignoredName, attrObj) in schemaAttrs:
                attrObjDuplicate, attributeValue = self.__dirty__[attrObj.attrname]
                # assert attrObjDuplicate is attrObj
                insertArgs.append(attributeValue)

            # XXX this isn't atomic, gross.
            self.store.executeSQL(self._baseInsertSQL(self.store), insertArgs)
            self.__everInserted = True
        # In case 1, we're dirty but we did an update, synchronizing the
        # database, in case 2, we haven't been created but we issue an insert.
        # In either case, the code in attributes.py sets the attribute *as well
        # as* populating __dirty__, so we clear out dirty and we keep the same
        # value, knowing it's the same as what's in the db.
        self.__dirty__.clear()
        if self.store.autocommit:
            self.committed()

    def upgradeVersion(self, typename, oldversion, newversion, **kw):
        # right now there is only ever one acceptable series of arguments here
        # but it is useful to pass them anyway to make sure the code is
        # functioning as expected
        assert typename == self.typeName, '%r != %r' % (typename, self.typeName)
        assert oldversion == self.schemaVersion
        assert newversion == oldversion + 1
        key = typename, newversion
        T = None
        if key in _legacyTypes:
            T = _legacyTypes[key]
        elif typename in _typeNameToMostRecentClass:
            mostRecent = _typeNameToMostRecentClass[typename]
            if mostRecent.schemaVersion == newversion:
                T = mostRecent
        if T is None:
            raise RuntimeError("don't know about type/version pair %s:%d" % (
                    typename, newversion))
        newTypeID = self.store.getTypeID(T) # call first to make sure the table
                                            # exists for doInsert below

        new = T(store=self.store,
                __justUpgraded=True,
                storeID=self.storeID,
                **kw)

        new.touch()
        new.activate()

        # XXX TODO; this needs to be forced to fall out of cache in the case of
        # an in memory revert
        if not new.__legacy__:
            self.store.objectCache.cache(self.storeID, new)

        self.store.executeSchemaSQL(_schema.CHANGE_TYPE,
                                    [newTypeID, self.storeID])
        self.deleteFromStore(False)
        return new

    def dependentItems(self):
        for cascadingAttr in (_cascadingDeletes.get(self.__class__, []) +
                              _cascadingDeletes.get(None, [])):
            for cascadedItem in self.store.query(cascadingAttr.type,
                                                 cascadingAttr == self):
                yield cascadedItem


    def deleteFromStore(self, deleteObject=True):
        # go grab dependent stuff
        if deleteObject:
            for dependent in self.dependentItems():
                dependent.deleteFromStore()

        self.touch()

        self.__deleting = True
        self.__deletingObject = deleteObject

        if self.store.autocommit:
            self.checkpoint()


    # You may specify schemaVersion and typeName in subclasses
    schemaVersion = None
    typeName = None

    ###### SQL generation ######

    def _baseSelectSQL(cls, st):
        if cls not in st.typeToSelectSQLCache:
            st.typeToSelectSQLCache[cls] = ' '.join(['SELECT * FROM',
                                                     st.getTableName(cls),
                                                     'WHERE',
                                                     st.getShortColumnName(cls.storeID),
                                                     '= ?'
                                                     ])
        return st.typeToSelectSQLCache[cls]

    _baseSelectSQL = classmethod(_baseSelectSQL)

    def _baseInsertSQL(cls, st):
        if cls not in st.typeToInsertSQLCache:
            attrs = list(cls.getSchema())
            qs = ', '.join((['?']*(len(attrs)+1)))
            st.typeToInsertSQLCache[cls] = (
                'INSERT INTO '+
                st.getTableName(cls) + ' (' + ', '.join(
                    [ st.getShortColumnName(cls.storeID) ] +
                    [ st.getShortColumnName(a[1]) for a in attrs]) +
                ') VALUES (' + qs + ')')
        return st.typeToInsertSQLCache[cls]

    _baseInsertSQL = classmethod(_baseInsertSQL)

    def _baseDeleteSQL(cls, st):
        if cls not in st.typeToDeleteSQLCache:
            st.typeToDeleteSQLCache[cls] = ' '.join(['DELETE FROM',
                                                     st.getTableName(cls),
                                                     'WHERE',
                                                     st.getShortColumnName(cls.storeID),
                                                     '= ? '
                                                     ])
        return st.typeToDeleteSQLCache[cls]

    _baseDeleteSQL = classmethod(_baseDeleteSQL)

    def _updateSQL(self):
        # XXX no point in caching for every possible combination of attribute
        # values - probably.  check out how prepared statements are used in
        # python sometime.
        dirty = self.__dirty__.items()
        if not dirty:
            raise RuntimeError("Non-dirty item trying to generate SQL.")
        dirty.sort()
        dirtyColumns = []
        dirtyValues = []
        for dirtyAttrName, (dirtyAttribute, dirtyValue) in dirty:
            dirtyColumns.append(self.store.getShortColumnName(dirtyAttribute))
            dirtyValues.append(dirtyValue)
        stmt = ' '.join([
            'UPDATE', self.store.getTableName(self.__class__), 'SET',
             ', '.join(['%s = ?'] * len(dirty)) %
              tuple(dirtyColumns),
            'WHERE ', self.store.getShortColumnName(type(self).storeID), ' = ?'])
        dirtyValues.append(self.storeID)
        return stmt, dirtyValues


    def getTableName(cls, store):
        """
        Retrieve a string naming the database table associated with this item
        class.
        """
        return store.getTableName(cls)
    getTableName = classmethod(getTableName)


    def getTableAlias(cls, store, currentAliases):
        return None
    getTableAlias = classmethod(getTableAlias)



class _PlaceholderColumn(_ContainableMixin, _ComparisonOperatorMuxer,
                         _MatchingOperationMuxer, _OrderingMixin):
    """
    Wrapper for columns from a L{Placeholder} which provides a fully qualified
    name built with a table alias name instead of the underlying column's real
    table name.
    """
    implements(IColumn)

    def __init__(self, placeholder, column):
        self.type = placeholder
        self.column = column

    def __repr__(self):
        return '<Placeholder %r>' % (self.column,)


    def compare(self, other, op):
        return compare(self, other, op)


    def getShortColumnName(self, store):
        return self.column.getShortColumnName(store)


    def getColumnName(self, store):
        assert self.type._placeholderTableAlias is not None, (
            "Placeholder.getTableAlias() must be called "
            "before Placeholder.attribute.getColumnName()")

        return '%s.%s' % (self.type._placeholderTableAlias,
                          self.column.getShortColumnName(store))

    def infilter(self, pyval, oself, store):
        return self.column.infilter(pyval, oself, store)


    def outfilter(self, dbval, oself):
        return self.column.outfilter(dbval, oself)



_placeholderCount = 0

class Placeholder(object):
    """
    Wrap an existing L{Item} type to provide a different name for it.

    This can be used to join a table against itself which is useful for
    flattening normalized data.  For example, given a schema defined like
    this::

        class Tag(Item):
            taggedObject = reference()
            tagName = text()


        class SomethingElse(Item):
            ...


    It might be useful to construct a query for instances of SomethingElse
    which have been tagged both with C{"foo"} and C{"bar"}::

        t1 = Placeholder(Tag)
        t2 = Placeholder(Tag)
        store.query(SomethingElse, AND(t1.taggedObject == SomethingElse.storeID,
                                       t1.tagName == u"foo",
                                       t2.taggedObject == SomethingElse.storeID,
                                       t2.tagName == u"bar"))
    """
    _placeholderTableAlias = None

    def __init__(self, itemClass):
        global _placeholderCount

        self._placeholderItemClass = itemClass
        self._placeholderCount = _placeholderCount + 1
        _placeholderCount += 1


    def __cmp__(self, other):
        """
        Provide a deterministic sort order between Placeholder instances.
        Those instantiated first will compare as less than than instantiated
        later.
        """
        if isinstance(other, Placeholder):
            return cmp(self._placeholderCount, other._placeholderCount)
        return NotImplemented


    def __getattr__(self, name):
        if name == 'storeID' or name in dict(self._placeholderItemClass.getSchema()):
            return _PlaceholderColumn(self, getattr(self._placeholderItemClass, name))
        raise AttributeError(name)


    def getSchema(self):
        return self._placeholderItemClass.getSchema()


    def getTableName(self, store):
        return self._placeholderItemClass.getTableName(store)


    def getTableAlias(self, store, currentAliases):
        if self._placeholderTableAlias is None:
            self._placeholderTableAlias = 'placeholder_' + str(len(currentAliases))
        return self._placeholderTableAlias



_legacyTypes = {}               # map (typeName, schemaVersion) to dummy class

def declareLegacyItem(typeName, schemaVersion, attributes, dummyBases=()):
    """
    Generate a dummy subclass of Item that will have the given attributes,
    and the base Item methods, but no methods of its own.  This is for use
    with upgrading.

    @param typeName: a string, the Axiom TypeName to have attributes for.
    @param schemaVersion: an int, the (old) version of the schema this is a proxy
    for.
    @param attributes: a dict mapping {columnName: attr instance}

    @param dummyBases: a sequence of 4-tuples of (baseTypeName,
    baseSchemaVersion, baseAttributes, baseBases) representing the dummy bases
    of this legacy class.
    """
    if (typeName, schemaVersion) in _legacyTypes:
        return _legacyTypes[typeName, schemaVersion]
    if dummyBases:
        realBases = [declareLegacyItem(*A) for A in dummyBases]
    else:
        realBases = (Item,)
    attributes = attributes.copy()
    attributes['__module__'] = 'item_dummy'
    attributes['__legacy__'] = True
    attributes['typeName'] = typeName
    attributes['schemaVersion'] = schemaVersion
    result = type(str('DummyItem<%s,%d>' % (typeName, schemaVersion)),
                  realBases,
                  attributes)
    assert result is not None, 'wtf, %r' % (type,)
    _legacyTypes[(typeName, schemaVersion)] = result
    return result



class _PowerupConnector(Item):
    """
    I am a connector between the store and a powerup.
    """
    typeName = 'axiom_powerup_connector'

    powerup = reference()
    item = reference()
    interface = text()
    priority = integer()


POWERUP_BEFORE = 1              # Priority for 'high' priority powerups.
POWERUP_AFTER = -1              # Priority for 'low' priority powerups.

