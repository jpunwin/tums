import config, os
from Core import Utils, PBXUtils

class Plugin(object):
    parameterHook = "--debzaptel"
    parameterDescription = "Install Zaptel Drivers"
    parameterArgs = ""
    autoRun = False
    required = "debian"
    configFiles = []

    kernelModules = [
        "zaphfc",
        "qozap",
        "ztgsm",
        "wctdm",
        "wctdm24xxp",
        "wcfxo",
        "wcfxs",
        "pciradio",
        "tor2",
        "torisa",
        "wct1xxp",
        "wct4xxp",
        "wcte11xp",
        "wanpipe",
        "wcusb",
        "xpp_usb" ]

    zaptelbasename = "zaptel-modules"

    modulesDir = "/lib/modules"

    zaptelModuleDirectory = "/misc"

    zaptelaptpkg = ""

    kernelVersion = ""

    modulesconfigfile = "/etc/modules"

    def reloadServices(self):
        self.loadModules()
        if(os.path.exists("/etc/zaptel.conf")):
            os.system('/etc/init.d/zaptel restart')
            os.system('/sbin/ztcfg -vv')
    
    def writeConfig(self, *a):
        """Writes the configuration files for zaptel to load at boot time"""
        if not PBXUtils.enabled():
            print "PBX System is not enabled"
            return
        if not self.checkModules():
            if not self.installModules():
                print "No automatic kernel support for zaptel detected please manually install Zaptel drivers ..."
                return
        try:
            module_config = open(self.modulesconfigfile, 'r')
            missing_modules = []
            missing_modules += self.kernelModules
            file_lines = module_config.readlines()
            for module in file_lines:
                module = module.rstrip()
                if module in missing_modules:
                   #If the module is in the config remove it from the missing_modules list
                   missing_modules.remove(module)
            module_config.close()
            if len(missing_modules) > 0:
                #If missing_modules has elements we need to add it to the /etc/modules file
                file_lines = [line.rstrip() for line in file_lines]
                file_lines += ["","#Generated by vulani configurator"]
                file_lines += missing_modules
                module_config = open(self.modulesconfigfile,'wt')
                module_config.write(str.join('\n', file_lines))
                module_config.close()
                #Load modules
                self.loadModules()

        except Exception, _e:
            print "Error loading config file %s, %s" % (self.modulesconfigfile, str(_e))

        try:
            hardware = PBXUtils.PBXHardware()
            if "zaptel" in hardware.plugins.keys():
                hardware.plugins["zaptel"].save()
                self.reloadServices()
        except Exception, _e:
            print "Error while applying configuration settings", str(_e)

        return
       

    def checkModules(self):
        """Check that the zaptel module exists and is installed for the current kernel return True if it does"""
        try:
            """Acquire the kernel version by running uname -r"""
            uname_output = os.popen('/bin/uname -r')
            self.kernelVersion = uname_output.readlines()[0].rstrip() #strip off the trailing spaces and \n
        except:
            print "Unable to acquire kernel version..."
            return False
        if len(self.kernelVersion) < 1: #This is to be double sure we have something work with
            print "Invalid kernel version details returned ..."
            return False
        
        #Build the sudo module name for this kernel zaptelModelName + '-' + kernelVersion
        self.zaptelaptpkg = self.zaptelbasename + '-' + self.kernelVersion
        #return the result of os.path.exists for zaptel.ko zaptel.ko note that this may break if the default location is moved
        #in that case we should rather scan the directory however this is unlikely to happen
        return os.path.exists(self.modulesDir + "/" + self.kernelVersion + self.zaptelModuleDirectory + "/zaptel.ko")

    def installModules(self):
        """Uses aptitude to check if a module exists in the repo and to install it if it does"""
        if len(self.zaptelaptpkg) < 1:
            return False
        apt_result = ""
        try:
            """Acquire information for the package"""
            aptitude_output = os.popen("/usr/bin/aptitude search %s" % self.zaptelaptpkg)
            resLines = aptitude_output.readlines()
            if(len(resLines) > 0):
                apt_result = aptitude_output.readlines()[0].rstrip()
            else:
                apt_result = ""
        except Exception, _e:
            #should not get here but if we do we should let everyone know
            print "Exception occured when attempting to run aptitude, %s" % _e
            return False

        if len(apt_result.split()) < 2:
            #Hmm aptitude could not find the kernel mod so therefore let the user know
            print "No packages found for zaptel Driver, attempting to build"
            os.system('aptitude update; m-a -iqt prepare; m-a -qti update && m-a -qti a-i zaptel')
            if self.checkModules():
                print "Zaptel Drivers installed successfully"
                return True
            else:
                print "Error Failed to install zaptel drivers"
                return False
                
        if apt_result.split()[0].lower() == "i":
            #should never get here but just in case
            print "EEEK - Please notify developer the modules are not in the right directory and the package shows as installed"
            return False

        print "Zaptel Drivers not installed, attempting to install (%s)." % self.zaptelaptpkg
        os.system('DEBIAN_FRONTEND="noninteractive" apt-get -y -q --force-yes install ' + self.zaptelaptpkg + ' > /dev/null 2>&1')
        if self.checkModules():
            print "Zaptel Drivers installed successfully"
            return True
        else:
            print "Error Failed to install zaptel drivers"
            return False

    def loadModules(self):
        #Reload the modules
        os.system('/etc/init.d/module-init-tools restart > /dev/null 2>&1')
