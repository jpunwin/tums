import config, os
from Core import Utils
import socket, struct

class Plugin(object):
    parameterHook = "--tuning"
    parameterDescription = "Perform system tuning"
    parameterArgs = ""
    autoRun = True
    configFiles = []

    def reloadServices(self):
        pass

    def writeConfig(self, *a):
        sysctrl = """
# /etc/sysctl.conf - Configuration file for setting system variables
# See sysctl.conf (5) for information.
# Auto-generated by TUMS

#kernel.domainname = example.com
#net/ipv4/icmp_echo_ignore_broadcasts=1

# the following stops low-level messages on console
kernel.printk = 4 4 1 7

##############################################################3
# Functions previously found in netbase
#

# Source route verification
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.rp_filter = 1

net.ipv4.conf.all.forwarding=1
net.ipv4.conf.all.arp_announce=1
net.ipv4.conf.all.arp_ignore=1
net.ipv4.conf.default.arp_announce=1
net.ipv4.conf.default.arp_ignore=1
#net.ipv6.conf.all.forwarding=1
"""
        if config.General.get('tuning', False):
            if config.General['tuning'].get('tcp-hp', False):
                # Tuning for GigE TCP
                # Default - 110592
                sysctrl+= "net.core.rmem_max=%s\n" % config.General['tuning']['tcp-hp'].get('max-window', '16777216')   
                # Default - 110592
                sysctrl+= "net.core.wmem_max=%s\n" % config.General['tuning']['tcp-hp'].get('max-window', '16777216')
                # Default - 4096    16384   131072
                sysctrl+= "net.ipv4.tcp_rmem=4096 87380 %s\n" % config.General['tuning']['tcp-hp'].get('max-window', '16777216') 
                # Default - 4096    87380   131072
                sysctrl+= "net.ipv4.tcp_wmem=4096 65536 %s\n" % config.General['tuning']['tcp-hp'].get('max-window', '16777216') 
                # Default - 1000
                sysctrl+= "net.core.netdev_max_backlog=%s\n" %config.General['tuning']['tcp-hp'].get('backlog', '250000')   
                
                if config.General['tuning']['tcp-hp'].get('selective-ack', True):
                    # Default - 1
                    sysctrl += "net.ipv4.tcp_sack=1\n"
                else:
                    sysctrl += "net.ipv4.tcp_sack=0\n"

            # SYN Cookies (Default off)
            if config.General['tuning'].get('syn-cookies', False):
                sysctrl += "net.ipv4.tcp_syncookies=1\n"

            # Proxy ARP  (Default off)
            if config.General['tuning'].get('proxyarp', False):
                sysctrl += "net.ipv4.conf.all.proxy_arp=1\n"
        
        l = open('/etc/sysctl.conf', 'wt')
        l.write(sysctrl)
        l.close()
