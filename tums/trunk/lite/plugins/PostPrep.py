import config, os, time, copy
import LDAP
from Core import Utils

class Plugin(object):
    parameterHook = "--postprep"
    parameterDescription = "Run TCS postprep configurations"
    parameterArgs = ""
    autoRun = False
    configFiles = []
    domain = config.Domain

    def reloadServices(self):
        pass

    def validateAttributes(self, data, newRecord):
        if data['userPermissions.employeeType']:
            newRecord['employeeType'].append('squid')

        if data.get('userPermissions.tumsAdmin', None):
            newRecord['employeeType'].append('tumsAdmin')

        elif data.get('userPermissions.tumsUser', None):
            tuenc = 'tumsUser[%s]' % ','.join(data['userPermissions.tumsUser'])
            newRecord['employeeType'].append(tuenc)

        if data.get('userPermissions.tumsReports', None):
            newRecord['employeeType'].append('tumsReports')

        if data['userPermissions.accountStatus']:
            newRecord['accountStatus'] = [ 'active' ]

        mFA = []
        for i in xrange(10):
            if data['mailSettings.mailForwardingAddress%s' % i]:
                ad = data['mailSettings.mailForwardingAddress%s' % i].replace(' ', '').replace('\r','')
                if ad:
                    mFA.append(ad)
        if mFA:
            newRecord['mailForwardingAddress'] = [ le.encode() for le in mFA ]

        mAA = []
        for i in xrange(10):
            if data['mailSettings.mailAlternateAddress%s' % i]:
                ad = data['mailSettings.mailAlternateAddress%s' % i].replace(' ', '').replace('\r','')
                if ad:
                    mAA.append(ad)
        if mAA:
            newRecord['mailAlternateAddress'] = [ le.encode().strip('\r') for le in mAA ]

        if data['userSettings.userPassword']:
            newRecord['userPassword'] = [
                "{SHA}"+LDAP.hashPassword(data['userSettings.userPassword'].encode())
            ]
        else:
            clearPassword = sha.sha("%s%s%s" % (alpha, time.time(),random.randint(1, 4000))).hexdigest()
            newRecord['userPassword'] = ["{SHA}"+LDAP.hashPassword(clearPassword)]

    def addEntry(self, newRecord, user, accountStatus):
        l = LDAP.createLDAPConnection('127.0.0.1', 'o='+config.LDAPBase,'cn=Manager', config.LDAPPassword)
        dc = "%s,%s,o=%s" % ('ou=People', LDAP.domainToDC(config.Domain), config.LDAPBase)

        try:
            LDAP.addElement(l, 'uid=%s,%s' % (user, dc), newRecord)
        except Exception, L:
            return 1
        # Send a mail to the luser to enable it...
        
    def submitForm(self, ctx, form, data):
        user = data['userSettings.uid'].encode().lower()
        data['userSettings.uid'] = user
        emailAddress = "%s@%s" % (user, self.domain)
        if not data['userSettings.sn']:
            data['userSettings.sn'] = "-"
        if not data['userSettings.givenName']:
            data['userSettings.givenName'] = user.capitalize()
    
        # Acquire local SID
        l = LDAP.createLDAPConnection('127.0.0.1', 'o='+config.LDAPBase, 'cn=Manager', config.LDAPPassword)
        dc = "%s,o=%s" % (LDAP.domainToDC(self.domain), config.LDAPBase)
        domainData =  LDAP.getDomInfo(l, dc, config.SambaDomain)
        
        SID = str(domainData['sambaSID'][0])

        if data['userSettings.userPassword']:
            clearPassword = data['userSettings.userPassword'].encode()
        else:
            clearPassword = sha.sha("%s" % random.randint(1, 4000)).hexdigest()

        # Construct NTLM hashes. 
        (LM, NT) = tuple(os.popen('/usr/local/tcs/tums/ntlmgen/ntlm.pl %s' % (clearPassword)).read().strip('\n').split())

        # Acquire UID offset
        uidOffset =  int(domainData['uidNumber'][0])

        # Make RID
        SIDOffset = 2*uidOffset

        # Append user to Domain Users
        try:
            domainUsers = LDAP.getDomUsers(l, dc)
            newDomainUsers = copy.deepcopy(domainUsers)
            if not newDomainUsers.get('memberUid', None): # Very very new domain
                newDomainUsers['memberUid'] = []
            newDomainUsers['memberUid'].append(user)
            LDAP.modifyElement(l, 'cn=Domain Users,ou=Groups,'+dc, domainUsers, newDomainUsers)
        except:
            pass # User already in group
        
        # Increment UID for domain
        newDom = copy.deepcopy(domainData)
        newDom['uidNumber'] = [str(uidOffset+1)]
        try: 
            LDAP.modifyElement(l, 'sambaDomainName=%s,%s,o=%s' % 
                (config.SambaDomain, LDAP.domainToDC(self.domain), config.LDAPBase), domainData, newDom)
        except:
            pass # User has a uid or something
        
        timeNow = str(int(time.time()))
        # LDAP template for SAMBA
        newRecord = {
            'sambaPrimaryGroupSID': [SID+"-"+str(1000+SIDOffset+1)],
            'sambaSID':             [SID+"-"+str(1000+SIDOffset)],
            'gidNumber':            ['513'],
            'uidNumber':            [str(uidOffset)],
            'sambaPasswordHistory': ['0000000000000000000000000000000000000000000000000000000000000000'],
            'sambaPwdMustChange':   ['2147483647'],
            'sambaPwdCanChange':    [timeNow],
            'sambaNTPassword':      [NT],
            'sambaLMPassword':      [LM],
            'gecos':                ['System User'],
            'sn':                   [data['userSettings.sn'].encode()],
            'givenName':            [data['userSettings.givenName'].encode()],
            'cn':                   ["%s %s" % (data['userSettings.givenName'].encode(), data['userSettings.sn'].encode())],
            'o':                    [config.CompanyName],
            'objectClass':          ['top', 'inetOrgPerson', 'posixAccount', 'shadowAccount',
                                     'SambaSamAccount', 'thusaUser'],
            'loginShell':           ['/bin/bash'],
            'sambaPwdLastSet':      [timeNow],
            'sambaAcctFlags':       ['[U          ]'],
            'mailMessageStore':     ['/var/spool/mail/' + emailAddress],
            'mail':                 [emailAddress],
            'homeDirectory':        ['/home/%s' % user],
            'uid':                  [user],
            'employeeType':         []
        }

        self.validateAttributes(data, newRecord)

        self.addEntry(newRecord, user, data['userPermissions.accountStatus'])
        
    def createAdmin(self):
        submitData = {
            'userSettings.uid': u'administrator',
            'userPermissions.employeeType': True, 'userPermissions.tumsUser': None,
            'userSettings.userPassword': "admin123", 'mailSettings.vacation': None,
            'mailSettings.mailAlternateAddress0': 'root@%s' % config.Domain,
            'mailSettings.mailAlternateAddress1': 'notify@%s' % config.Domain,
            'mailSettings.mailAlternateAddress2': 'postmaster@%s' % config.Domain,
            'userPermissions.tumsAdmin': True,
            'mailSettings.mailForwardingAddress0': 'notify@thusa.co.za',
            'userPermissions.accountStatus': True,
            'userPermissions.employeeType':True,
            'userSettings.sn': u'Admin', 'userSettings.givenName': u'System'
        }
        for i in range(10):
            if not submitData.get('mailSettings.mailAlternateAddress%s' % i, None):
                submitData['mailSettings.mailAlternateAddress%s' % i] = u""
            if not submitData.get('mailSettings.mailForwardingAddress%s' % i, None):
                submitData['mailSettings.mailForwardingAddress%s' % i] = u""
        form = None
        self.submitForm(None, form, submitData)

    def writeConfig(self, *a):
        # make sure slapd is stopped
        os.system('/etc/init.d/slapd stop')
        # Back up ldap.. Who knows.. someone just might postprep a live box :(
        os.system('slapcat > /usr/local/tcs/tums/backups/ldap-%s.ldif' % int(time.time()))

        # Kill the ldap database because 1.2rc3 came with cruf in it for some reason
        if os.path.exists('/etc/debian_version'): # check for debian base
            os.system('rm /var/lib/ldap/*')
        else:
            os.system('rm /var/lib/openldap-data/*')

        # Start SLAPd 
        os.system('/etc/init.d/slapd start')
        # Make sure it's started...
        lk = os.popen('/etc/init.d/slapd status').read()
        if "stopped" in lk:
            print "slapd isn't running, and I can't start it :-(."
            print "the LDAP service is probably broken."
            return
        # Generate a shiny new tree
        os.system('/usr/local/tcs/tums/genLDAP.py')
        # Import the new tree
        os.system('/etc/init.d/slapd stop')
        os.system('slapadd < /usr/local/tcs/tums/template.ldif') # ldapadd is fucked on Debian
        os.system('/etc/init.d/slapd start')
        # Restart slapd for safe measure
        os.system('/etc/init.d/slapd restart')
        os.system('/etc/init.d/samba restart')

        # Populate the LDAP tree with SMB goodness
        os.system('smbldap-populate')
        # Sprinkle on a bit of joy and sugar
        os.system('/usr/local/tcs/tums/ldapConfig')
        # Secure it with a password
        if os.path.exists('/etc/debian_version'):
            os.system('smbpasswd -w `cat /etc/ldap/slapd.conf | grep rootpw | awk \'{print $2}\'`')        
        else:
            os.system('smbpasswd -w `cat /etc/openldap/slapd.conf | grep rootpw | awk \'{print $2}\'`')
        # And then switch it off again
        os.system('/etc/init.d/samba stop')

        os.system('/usr/local/tcs/tums/syscripts/vpn.sh')

        # Clear samba cache
        os.system('rm /var/cache/samba/wins.dat')
        os.system('rm /var/cache/samba/gencache.tdb')
        os.system('rm /var/cache/samba/browse.dat')

        os.system('rm /etc/bind/pri/*.jnl')

        os.system('/root/tcs/vpn.sh')
        if os.path.exists('/etc/debian_version'):
            os.system('openssl req -x509 -newkey rsa:1024 -keyout /etc/exim4/exim.key -out /etc/exim4/exim.cert -days 9999 -nodes')
        else:
            os.system('openssl req -x509 -newkey rsa:1024 -keyout /etc/exim/exim.key -out /etc/exim/exim.cert -days 9999 -nodes')

        os.system('sensors-detect')

        os.system('ntpdate -su %s' % config.NTP)

        if not os.path.exists('/etc/debian_version'):
            os.system('/etc/init.d/clock save')
        
        # Recreate openssh-server keys if it's gentoo
        if not os.path.exists('/etc/debian_version'):
            os.system('rm /etc/ssh/ssh*key*')
            os.system('rm /root/.ssh/known_hosts')

        runlevels =  [
            ('apache2',  'default'),
            ('slapd',  'default'),
            ('mysql',  'default'),
            ('exim',  'default'),
            ('clamd', 'default'),
            ('courier-imapd',  'default'),
            ('courier-authlib',  'default'),
            ('courier-pop3d',  'default'),
            ('ddclient', 'default'),
            ('shorewall', 'default'),
            ('spamd', 'default'),
            ('squid', 'default'),
            ('smartd', 'default'),
            ('sysklogd', 'default'),
            ('ulogd', 'default'),
            ('xinetd', 'default'),
            ('cupsd', 'default'),
            ('netmount', 'default'),
            ('ntp-client', 'default'),
            ('ntpd', 'default'),
            ('gpm', 'default'),
            ('samba', 'default'),
            ('nscd', 'default'),
            ('named', 'default'),
            ('dhcpd', 'default'),
            ('tums', 'default'),
            ('quagga', 'default'),
            ('zebra', 'default')
        ]

        if os.path.exists('/etc/debian_version'):
            for run, level in runlevels:
                # apply modifications for debian
                level = level.replace('default', 'defaults')
                run = run.replace('dhcpd', 'dhcp3-server').replace('exim', 'exim4')
                run = run.replace('courier-authlib', 'courier-authdaemon')
                os.system('update-rc.d %s %s > /dev/null 2>&1' % (run, level))

            # Do defaults fixes (bloody irritating...)
            spamd = """ENABLED=1
OPTIONS="--create-prefs --max-children 5 --helper-home-dir"
PIDFILE="/var/run/spamd.pid"
NICE="--nicelevel 15"""
            Utils.writeConf('/etc/default/spamassassin', spamd, '#')

            shorewall = """startup=1\n"""
            Utils.writeConf('/etc/default/shorewall', shorewall, '#')

            os.system('update-rc.d -f fprobe remove > /dev/null 2>&1')

        else:
            for inter in config.EthernetDevices:
                runlevels.append(("net."+inter, 'boot'))

            for inter in config.WANDevices:
                runlevels.append(("net."+inter, 'boot'))

            for run,level in runlevels:
                os.system('rc-update add %s %s' % (run, level))

        os.system('chmod +x /usr/local/tcs/tums/existat.py')
        os.system('chmod +x /usr/local/tcs/tums/existat-render.py')

        print "Creating admin account"
        self.createAdmin()


