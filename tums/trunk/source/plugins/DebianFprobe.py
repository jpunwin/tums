import config, os
from Core import Utils

class Plugin(object):
    """ Configures everything needed for Debian fprobe-ulog. """
    parameterHook = "--fprobe"
    parameterDescription = "Reconfigure fprobe for Debian"
    parameterArgs = ""
    autoRun = True
    required = "debian"
    configFiles = [ 
        "/etc/default/fprobe-ulog",
    ]

    def reloadServices(self):
        os.system('/etc/init.d/fprobe-ulog restart')

    def writeConfig(self, *a):
        lans = Utils.getLans(config)
        wans = Utils.getWans(config)

        lanifaces = ','.join(["%s:100" % i for i in lans])
        wanifaces = ','.join(["%s:%s" % (iface, 201+c) for c, iface in enumerate(wans)])

        ifaces = "%s,%s" % (lanifaces, wanifaces)
        ifaces = ifaces.strip(',') # Take care of any trailing commas if wanifaces is empty

        # Declare the configuration
        fprobe = """
#fprobe-ulog configuration generated by TUMS

INTERFACE="%s"
FLOW_COLLECTOR="127.0.0.1:9685"
OTHER_ARGS="-U2"
""" % ifaces

        l = open('/etc/default/fprobe-ulog', 'wt')
        l.write(fprobe)
        l.close()
