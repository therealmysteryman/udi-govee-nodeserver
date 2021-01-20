#!/usr/bin/env python3

"""
This is a NodeServer for Twinkly written by automationgeek (Jean-Francois Tremblay)
based on the NodeServer template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com
"""

import polyinterface
import hashlib
import asyncio
import warnings 
import time
import json
import sys
from copy import deepcopy
from govee_api_laggat import Govee, GoveeAbstractLearningStorage, GoveeLearnedInfo

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

def get_profile_info(logger):
    pvf = 'profile/version.txt'
    try:
        with open(pvf) as f:
            pv = f.read().replace('\n', '')
    except Exception as err:
        logger.error('get_profile_info: failed to read  file {0}: {1}'.format(pvf,err), exc_info=True)
        pv = 0
    f.close()
    return { 'version': pv }

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Govee'
        self.initialized = False
        self.queryON = False
        self.api = ""
        self.tries = 0
        self.hb = 0

    def start(self):
        LOGGER.info('Started Twinkly for v2 NodeServer version %s', str(VERSION))
        self.setDriver('ST', 0)
        try:
            if 'api' in self.polyConfig['customParams']:
                self.api = self.polyConfig['customParams']['api']
            else:
                self.api = ""
                  
            if 'nbDevices' in self.polyConfig['customParams']:
                self.nbDevices = self.polyConfig['customParams']['nbDevices']
            else:
                self.nbDevices = 1

            if self.api == "" :
                LOGGER.error('Govee requires \'api\' parameters to be specified in custom configuration.')
                return False
            else:
                self.check_profile()
                self.discover()
                
        except Exception as ex:
            LOGGER.error('Error starting Govee
           

    def shortPoll(self):
        self.setDriver('ST', 1)
        self.reportDrivers()
        for node in self.nodes:
            if  self.nodes[node].queryON == True :
                self.nodes[node].query()
                
    def longPoll(self):
        self.heartbeat()

    def heartbeat(self):
        LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def discover(self, *args, **kwargs):
        for i in range(int(self.nbDevices)):
            self.addNode(GoveeLight(self, self.address, "led" + str(i+1), "led" + str(i+1), self.api, i ))

    def delete(self):
        LOGGER.info('Deleting Govee')

    def check_profile(self):
        self.profile_info = get_profile_info(LOGGER)
        # Set Default profile version if not Found
        cdata = deepcopy(self.polyConfig['customData'])
        LOGGER.info('check_profile: profile_info={0} customData={1}'.format(self.profile_info,cdata))
        if not 'profile_info' in cdata:
            cdata['profile_info'] = { 'version': 0 }
        if self.profile_info['version'] == cdata['profile_info']['version']:
            self.update_profile = False
        else:
            self.update_profile = True
            self.poly.installprofile()
        LOGGER.info('check_profile: update_profile={}'.format(self.update_profile))
        cdata['profile_info'] = self.profile_info
        self.saveCustomData(cdata)

    def install_profile(self,command):
        LOGGER.info("install_profile:")
        self.poly.installprofile()

    id = 'controller'
    commands = {
        'QUERY': shortPoll,
        'DISCOVER': discover,
        'INSTALL_PROFILE': install_profile,
    }
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2}]

class GoveeLight(polyinterface.Node):

    def __init__(self, controller, primary, address, name, api_key, device_id):

        super(GoveeLight, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.api_key = api_key
        self.device_id = device_id

    def start(self):
        #self.query()
        pass

    def setOn(self, command):
        asyncio.run(self._turnOn())
        self.setDriver('ST', 100,True)
        
    def setOff(self, command):
        asyncio.run(self._turnOff())
        self.setDriver('ST', 0,True)
    
    def setBrightness(self, command):
        asyncio.run(self._setBrightness(int(command.get('value'))))
        self.setDriver('GV1', int(command.get('value')),True)
        
    def query(self):
        asyncio.run(self._query())
                         
    async def _query(self) : 
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        devices = (
            await govee.get_states()
        )
        print (devices)
        await govee.close()
    
    async def _turnOff(self) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        cache_device = await govee.device(devices[self.device_id].device) 
        success, err = await govee.turn_off(cache_device.device)
        await govee.close()
        
    async def _turnOn(self) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        cache_device = await govee.device(devices[self.device_id].device) 
        success, err = await govee.turn_on(cache_device.device)
        await govee.close()
        
    async def _setBrightness(self,bri) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        cache_device = await govee.device(devices[self.device_id].device) 
        success, err = await govee.set_brightness(cache_device, bri)
        await govee.close()
            
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 78},
               {'driver': 'GV1', 'value': 0, 'uom': 51}]

    id = 'GOVEE_LIGHT'
    commands = {
                    'DON': setOn,
                    'DOF': setOff,
                    'SET_BRI': setBrightness
                }

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('GoveeNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
