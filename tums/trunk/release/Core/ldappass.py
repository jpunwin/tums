"""
ldaputil.passwd - client-side password setting
(c) by Michael Stroeder <michael@stroeder.com>

This module is distributed under the terms of the
GPL (GNU GENERAL PUBLIC LICENSE) Version 2
(see http://www.gnu.org/copyleft/gpl.html)

Python compability note:
This module only works with Python 1.6+ since all string parameters
are assumed to be Unicode objects and string methods are used instead
string module.
"""

__version__ = '0.1.0'

import random,ldap

# Alphabet for encrypted passwords (see module crypt)
CRYPT_ALPHABET = './0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Try to determine the hash types available on the current system by
# checking all required modules are in place.
# After all AVAIL_USERPASSWORD_SCHEMES is a list of tuples containing
# [(hash-id,(hash-description)].
AVAIL_USERPASSWORD_SCHEMES = {
  'sha':'userPassword SHA-1',
  'ssha':'userPassword salted SHA-1',
  'md5':'userPassword MD5',
  'smd5':'userPassword salted MD5',
  'crypt':'userPassword Unix crypt',
  '':'userPassword plain text',
}

AVAIL_AUTHPASSWORD_SCHEMES = {
  'sha1':'authPassword SHA-1',
  'md5':'authPassword MD5',
}

_UnicodeType = type(u'')

def _remove_dict_items(l,rl):
  """
  Not for public use:
  Remove a list item ignoring ValueError: list.remove(x): x not in list
  """
  for i in rl:
    try:
      del l[i]
    except KeyError:
      pass

try:
  import base64
except ImportError:
  _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES,['md5','smd5','sha','ssha'])
  _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES,['md5','sha1'])
else:
  try:
    # random is needed for salted hashs
    import random
  except ImportError:
    _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES,['crypt','smd5','ssha'])
    _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES,['md5','sha1'])
  else:
    random.seed()
  try:
    import sha
  except ImportError:
    _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES,['sha','ssha'])
    _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES,['sha1'])
  try:
    import md5
  except ImportError:
    _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES,['md5','smd5'])
    _remove_dict_items(AVAIL_AUTHPASSWORD_SCHEMES,['md5'])
  try:
    import crypt
  except ImportError:
    _remove_dict_items(AVAIL_USERPASSWORD_SCHEMES,['crypt'])


def _salt(saltLen=2,saltAlphabet=None):
  """
  Create a random salt.

  saltLen
      Requested length of salt string.
  saltAlphabet
      If non-zero string it is assumed to contain all valid chars
      for the salt. If zero-length or None the salt returned is an
      arbitrary octet string.
  """
  salt = []
  if saltAlphabet:
    saltAlphabetBounce = len(saltAlphabet)-1
    for i in range(saltLen):
      salt.append(saltAlphabet[random.randrange(0,saltAlphabetBounce)])
  else:
    for i in range(saltLen):
      salt.append(chr(random.randrange(0,255)))
  return ''.join(salt)


class Password:
  """
  Base class for plain-text LDAP passwords.
  """
  
  def __init__(self,l,dn=None,charset='utf-8'):
    """
    l
        LDAPObject instance to operate with. The application
        is responsible to bind with appropriate bind DN before(!)
        creating the Password instance.
    dn
        string object with DN of entry
    charset
        Character set for encoding passwords. Note that this might
        differ from the character set used for the normal directory strings.
    """
    self._l = l
    self._dn = dn
    self._multiple = 0
    self._charset = charset
    if not dn is None:
      result = self._l.search_s(
        self._dn,ldap.SCOPE_BASE,'(objectClass=*)',[self.passwordAttributeType]
      )
      if result:
        entry_data = result[0][1]
        self._passwordAttributeValue = entry_data.get(
          self.passwordAttributeType,entry_data.get(self.passwordAttributeType.lower(),[])
        )
      else:
        self._passwordAttributeValue = []
    else:
      self._passwordAttributeValue = []

  def _compareSinglePassword(self,testPassword,singlePasswordValue):
    """
    Compare testPassword with encoded password in singlePasswordValue.
    
    testPassword
        Plain text password for testing
    singlePasswordValue
        password to verify against
    """
    return testPassword==singlePasswordValue

  def comparePassword(self,testPassword):
    """
    Return 1 if testPassword is in self._passwordAttributeValue
    """
    if type(testPassword)==_UnicodeType:
      testPassword = testPassword.encode(self._charset)
    for p in self._passwordAttributeValue:
      if self._compareSinglePassword(testPassword,p):
        return 1
    return 0

  def _delOldPassword(self,oldPassword):
    """
    Return list with all occurences of oldPassword being removed.
    """
    return [
      p
      for p in self._passwordAttributeValue
      if not self._compareSinglePassword(oldPassword,p.strip())
    ]

  def encodePassword(self,plainPassword,scheme=None):
    """
    encode plainPassword into plain text password
    """
    if type(plainPassword)==_UnicodeType:
      plainPassword = plainPassword.encode(self._charset)
    return plainPassword

  def changePassword(self,oldPassword=None,newPassword=None,scheme=None):
    """
    oldPassword
      Old password associated with entry.
      If a Unicode object is supplied it will be encoded with
      self._charset.
    newPassword    
      New password for entry.
      If a Unicode object is supplied it will be encoded with
      charset before being transferred to the directory.
    scheme
        Hashing scheme to be used for encoding password.
        Default is plain text.
    charset
        This character set is used to encode passwords
        in case oldPassword and/or newPassword are Unicode objects.
    """
    if not oldPassword is None and type(oldPassword)==_UnicodeType:
      oldPassword = oldPassword.encode(charset)
    if self._multiple and not oldPassword is None:
      newPasswordValueList = self._delOldPassword(oldPassword)
    else:
      newPasswordValueList = []
    newPasswordValue = self.encodePassword(newPassword,scheme)
    newPasswordValueList.append(newPasswordValue)
    self._storePassword(oldPassword,newPasswordValueList)
    # In case a new password was auto-generated the application
    # has to know it => return it as result
    return newPassword

  def _storePassword(self,oldPassword,newPasswordValueList):
    """Replace the password value completely"""
    self._l.modify_s(
      self._dn,
      [
        (ldap.MOD_REPLACE,self.passwordAttributeType,newPasswordValueList)
      ]
    )


class UserPassword(Password):
  """
  Class for LDAP password changing in userPassword attribute

  RFC 2307:
    http://www.ietf.org/rfc/rfc2307.txt
  OpenLDAP FAQ:
    http://www.openldap.org/faq/data/cache/419.html
  Netscape Developer Docs:
    http://developer.netscape.com/docs/technote/ldap/pass_sha.html
  """
  passwordAttributeType='userPassword'
  _hash_bytelen = {'md5':16,'sha':20}


  def __init__(self,l=None,dn=None,charset='utf-8',multiple=0):
    """
    Like CharsetPassword.__init__() with one additional parameter:
    multiple
        Allow multi-valued password attribute.
        Default is single-valued (flag is 0).
    """
    self._multiple = multiple
    Password.__init__(self,l,dn,charset)

  def _hashPassword(self,password,scheme,salt=None):
    """
    Return hashed password (including salt).
    """
    scheme = scheme.lower()
    if not scheme in AVAIL_USERPASSWORD_SCHEMES.keys():
      raise ValueError,'Hashing scheme %s not supported for class %s.' % (
        scheme,self.__class__.__name__
      )
      raise ValueError,'Hashing scheme %s not supported.' % (scheme)
    if salt is None:
      if scheme=='crypt':
        salt = _salt(saltLen=2,saltAlphabet=CRYPT_ALPHABET)
      elif scheme in ['smd5','ssha']:
        salt = _salt(saltLen=4,saltAlphabet=None)
      else:
        salt = ''
    if scheme=='crypt':
      return crypt.crypt(password,salt)
    elif scheme in ['md5','smd5']:
      return base64.encodestring(md5.new(password+salt).digest()+salt).strip()
    elif scheme in ['sha','ssha']:
      return base64.encodestring(sha.new(password+salt).digest()+salt).strip()
    else:
      return password

  def _compareSinglePassword(self,testPassword,singlePasswordValue,charset='utf-8'):
    """
    Compare testPassword with encoded password in singlePasswordValue.
    
    testPassword
        Plain text password for testing. If Unicode object
        it is encoded using charset.
    singlePasswordValue
        {scheme} encrypted password
    """
    singlePasswordValue = singlePasswordValue.strip()
    try:
      scheme,encoded_p = singlePasswordValue[singlePasswordValue.find('{')+1:].split('}',1)
    except ValueError:
      scheme,encoded_p = '',singlePasswordValue
    scheme = scheme.lower()
    salt = ""
    if scheme in ['md5','sha','smd5','ssha']:
      hashed_p = base64.decodestring(encoded_p)
      if scheme in ['smd5','ssha']:
        pos = self._hash_bytelen[scheme[1:]]
        cmp_password,salt = hashed_p[:pos],hashed_p[pos:]
      else:
        cmp_password,salt = hashed_p,''
    hashed_password = self._hashPassword(testPassword,scheme,salt)
    return hashed_password==encoded_p

  def encodePassword(self,plainPassword,scheme):
    """
    encode plainPassword according to RFC2307 password attribute syntax
    """
    plainPassword = Password.encodePassword(self,plainPassword)
    if scheme:
      return ('{%s}%s' % (
        scheme.upper(),
        self._hashPassword(plainPassword,scheme)
      )).encode('ascii')
    else:
      return plainPassword


class AuthPassword(Password):
  """
  Class for LDAP password changing in authPassword attribute.
  
  RFC 3112:
    http://www.ietf.org/rfc/rfc3112.txt
  """
  passwordAttributeType='authPassword'

  def __init__(self,l=None,dn=None,charset='utf-8',multiple=0):
    """
    Like CharsetPassword.__init__() with one additional parameter:
    multiple
        Allow multi-valued password attribute.
        Default is single-valued (flag is 0).
    """
    self._multiple = multiple
    CharsetPassword.__init__(self,l,dn,charset)

  def _hashPassword(self,password,scheme,salt=None):
    """
    Returns tuple of hashed password (including salt), salt.
    """
    scheme = scheme.lower()
    if not scheme in AVAIL_AUTHPASSWORD_SCHEMES.keys():
      raise ValueError,'Hashing scheme %s not supported for class %s.' % (
        scheme,self.__class__.__name__
      )
    if salt is None:
      salt = _salt(saltLen=16,saltAlphabet=None)
    if scheme=='md5':
      return md5.new(password+salt).digest(),salt
    elif scheme=='sha1':
      return sha.new(password+salt).digest(),salt
    else:
      raise ValueError,'Hashing scheme %s not implemented for class %s.' % (
        scheme,self.__class__.__name__
      )

  def _compareSinglePassword(self,password,authPasswordValue):
    """
    Compare password with encoded password in singlePasswordValue.
    
    password
        Plain text password for testing
    singlePasswordValue
        {scheme} encrypted password
    """
    scheme,authInfo,authValue = tuple([
      p.strip()
      for p in authPasswordValue.split('$',2)
    ])
    authInfo = base64.decodestring(authInfo)
    authValue = base64.decodestring(authValue)
    hashed_password,dummy = self._hashPassword(password,scheme,authValue)
    return hashed_password==authInfo

  def encodePassword(self,plainPassword,scheme):
    """
    encode plainPassword according to RFC3112 attribute syntax
    """
    authInfo,authValue = self._hashPassword(
      Password.encodePassword(self,plainPassword),scheme
    )
    return ('%s $ %s $ %s' % (
      scheme,base64.encodestring(authInfo).strip(),
      base64.encodestring(authValue).strip()
    )).encode('ascii')


class UnicodePwd(Password):
  """
  Class for LDAP password changing in unicodePwd attribute
  on Active Directory servers.
  (see "HOWTO: Change a Windows 2000 User's Password Through
  LDAP" on http://support.microsoft.com/support/kb/articles/q269/1/90.ASP)
  """
  passwordAttributeType='unicodePwd'
  _multiple = 0

  def __init__(self,l=None,dn=None):
    """
    Like CharsetPassword.__init__() with one additional parameter.
    """
    Password.__init__(self,l,dn)
    self._charset = 'utf-16-le'

  def encodePassword(self,plainPassword,scheme=None):
    """
    Enclose Unicode password string in double-quotes.
    """
    return '"%s"' % (Password.encodePassword(self,plainPassword))

  def _storePassword(self,oldPassword,newPasswordValueList):
    """
    Two different use-cases:
    If the application sets oldPassword to None it is assumed
    that an admin resets a user's password
    => A single replace operation is used to reset the unicodePwd attribute.
    If oldPassword is not None it is assumed it is assumed that
    the user changes his/her own password
    => a delete followed by an add operation is used.
    """
    if oldPassword is None:
      self._l.modify_s(
        self._dn,
        [
          (ldap.MOD_REPLACE,self.passwordAttributeType,newPasswordValueList)
        ]
      )
    else:
      self._l.modify_s(
        self._dn,self.passwordAttributeType,
        [
          (ldap.MOD_DELETE,self.passwordAttributeType,oldPassword),
          (ldap.MOD_ADD,self.passwordAttributeType,newPasswordValueList[0])
        ]
      )

