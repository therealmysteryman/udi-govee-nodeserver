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
            if 'api_key' in self.polyConfig['customParams']:
                self.api_key = self.polyConfig['customParams']['api_key']
            else:
                self.api = ""

            if self.api_key == "" :
                LOGGER.error('Govee requires \'api_key\' parameters to be specified in custom configuration.')
                return False
            else:
                self.check_profile()
                self.discover()
                
        except Exception as ex:
            LOGGER.error('Error starting Govee')
           

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
        devices = asyncio.run(self._getDevices())
        for device in devices:
            strHashDevice = str(int(hashlib.md5(device.device.encode('utf8')).hexdigest(), 16) % (10 ** 8))
            self.addNode(GoveeLight(self, self.address, strHashDevice, strHashDevice, self.api_key, device.device ))

    def delete(self):
        LOGGER.info('Deleting Govee')

    async def _getDevices(self):
        try:
            govee = await Govee.create(self.api_key)
            ping_ms, err = await govee.ping()  # all commands as above
            devices, err = await govee.get_devices()
            await govee.close()
            return devices
        except Exception as ex:
            LOGGER.error('_getDevices:')
            
                
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
        self.query()

    def setOn(self, command):
        try:
            asyncio.run(self._turnOn())
            self.setDriver('ST', 100,True)
        except Exception as ex:
            LOGGER.error('setOn:', ex)
        
    def setOff(self, command):
        try:
            asyncio.run(self._turnOff())
            self.setDriver('ST', 0,True)
        except Exception as ex:
            LOGGER.error('setOff:', ex) 
    
    def setBrightness(self, command):
        try:
            asyncio.run(self._setBrightness(int(command.get('value'))))
            self.setDriver('GV1', int(command.get('value')),True)
        except Exception as ex:
            LOGGER.error('setBrightness:', ex)     
        
    def query(self):
        try:
            ps, bri = asyncio.run(self._query())
            if ps :
                self.setDriver('ST', 100, True)
            else :
                self.setDriver('ST', 0, True)
            self.setDriver('GV1', int(bri), True)
        except Exception as ex:
            LOGGER.error('query:', ex)   
        
    async def _query(self) : 
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        devices = (
            await govee.get_states()
        )
        for device in devices :
            if device.device == self.device_id :
                cached_device = device
                break
        await govee.close()
        return cached_device.power_state, cached_device.brightness
    
    async def _turnOff(self) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices() 
        for device in devices :
            if device.device == self.device_id :
                cached_device = device
                break 
        success, err = await govee.turn_off(cached_device.device)
        await govee.close()
        
    async def _turnOn(self) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        for device in devices :
            if device.device == self.device_id:
                cached_device = device
                break
        success, err = await govee.turn_on(cached_device.device)
        await govee.close()
        
    async def _setBrightness(self,bri) :
        govee = await Govee.create(self.api_key)
        ping_ms, err = await govee.ping()  # all commands as above
        devices, err = await govee.get_devices()
        for device in devices :
            if device.device == self.device_id:
                cached_device = device
                break
        success, err = await govee.set_brightness(cached_device, bri)
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
