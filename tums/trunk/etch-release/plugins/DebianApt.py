import config, os
from Core import Utils

class Plugin(object):
    """ Configures everything needed for Debian APT. """
    parameterHook = "--apt"
    parameterDescription = "Reconfigure APT on Debian"
    parameterArgs = ""
    autoRun = False
    required = "debian"
    configFiles = [ 
        "/etc/apt/sources.list",
    ]

    def reloadServices(self):
        #os.system('aptitude update')
        pass

    def writeConfig(self, *a):
        if config.General.get('aptrepo', None):
            l = open('/etc/apt/sources.list', 'wt')
            l.write('# Generated by TUMS Configurator \n\n')
            l.write('\n'.join(config.General['aptrepo']))
            l.write('\n\n')
            l.close()
