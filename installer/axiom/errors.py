# -*- test-case-name: axiom.test -*-

from twisted.cred.error import UnauthorizedLogin


class TimeoutError(Exception):
    """
    A low-level SQL operation timed out.

    @ivar statement: The SQL statement which timed out.
    @ivar timeout: The timeout, in seconds, which was exceeded.
    @ivar underlying: The backend exception which signaled this, or None.
    """
    def __init__(self, statement, timeout, underlying):
        Exception.__init__(self, statement, timeout, underlying)
        self.statement = statement
        self.timeout = timeout
        self.underlying = underlying



class BadCredentials(UnauthorizedLogin):
    pass



class NoSuchUser(UnauthorizedLogin):
    pass



class MissingDomainPart(NoSuchUser):
    """
    Raised when a login is attempted with a username which consists of only
    a local part.  For example, "testuser" instead of "testuser@example.com".
    """


class DuplicateUser(Exception):
    pass



class CannotOpenStore(RuntimeError):
    """
    There is a problem such that the store cannot be opened.
    """



class NoUpgradePathAvailable(CannotOpenStore):
    """
    No upgrade path is available, so the store cannot be opened.
    """



class NoCrossStoreReferences(AttributeError):
    """
    References are not allowed between items within different Stores.
    """



class SQLError(RuntimeError):
    """
    Axiom internally generated some bad SQL.
    """
    def __init__(self, sql, args, underlying):
        RuntimeError.__init__(self, sql, args, underlying)
        self.sql, self.args, self.underlying = self.args

    def __str__(self):
        return "<SQLError: %r(%r) caused %s: %s>" % (
            self.sql, self.args,
            self.underlying.__class__, self.underlying)



class UnknownItemType(Exception):
    """
    Can't load an item: it's of a type that I don't see anywhere in Python.
    """



class SQLWarning(Warning):
    """
    Axiom internally generated some CREATE TABLE SQL that ... probably wasn't bad
    """



class TableCreationConcurrencyError(RuntimeError):
    """
    Woah, this is really bad.  If you can get this please tell us how.
    """



class DuplicateUniqueItem(KeyError):
    """
    Found 2 or more of an item which is supposed to be unique.
    """



class ItemNotFound(KeyError):
    """
    Did not find even 1 of an item which was supposed to exist.
    """



class ItemClassesOnly(TypeError):
    """
    An object was passed to a method that wasn't a subclass of Item.
    """
