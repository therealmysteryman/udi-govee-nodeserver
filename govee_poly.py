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
        for node in self.nodes:
            if  self.nodes[node].queryON == True :
                self.nodes[node].update()
                
    def longPoll(self):
        self.heartbeat()

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()        
        
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
        'QUERY': query,
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
        self.update()

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
            self.setDriver('GV1', int(command.get('value')))
        except Exception as ex:
            LOGGER.error('setBrightness:', ex)     
    
    def setColor(self,command):
        try:
           
            color = []
        
            query = command.get('query')
            color_r = int(query.get('R.uom100'))
            color_g = int(query.get('G.uom100'))
            color_b = int(query.get('B.uom100'))    
        
            color.append(color_r)
            color.append(color_g)
            color.append(color_b)
                                
            asyncio.run(self._setColor(color))
            self.setDriver('GV6', color_r)
            self.setDriver('GV7', color_g)
            self.setDriver('GV8', color_b)

        except Exception as ex:
            LOGGER.error('setColor:', ex)     
    
    def update(self):
        try:
            ps, bri, color = asyncio.run(self._query())
            if ps :
                self.setDriver('ST', 100)
            else :
                self.setDriver('ST', 0)
            
            self.setDriver('GV1', int(bri))
                        
            self.setDriver('GV6', int(color[0]))
            self.setDriver('GV7', int(color[1]))
            self.setDriver('GV8', int(color[2]))
                        
        except Exception as ex:
            LOGGER.error('update:', ex)   
    
    def query(self):
        self.reportDrivers()
    
    async def _query(self) : 
        myDeviceState = None
                    
        govee = await Govee.create(self.api_key)
        devices, err = await govee.get_devices()
        devicesState = await govee.get_states()
                                
        for deviceState in devicesState :
            if deviceState.device == self.device_id :
                myDeviceState = deviceState
                break
        await govee.close()                
        if myDeviceState is not None :
            return myDeviceState.power_state, myDeviceState.brightness, myDeviceState.color
        else:
            return False, 0, (0,0,0) 

    async def _turnOff(self) :
        govee = await Govee.create(self.api_key)
        devices, err = await govee.get_devices() 
        success, err = await govee.turn_off(self.device_id)
        await govee.close()
        
    async def _turnOn(self) :
        govee = await Govee.create(self.api_key)
        devices, err = await govee.get_devices()
        success, err = await govee.turn_on(self.device_id)
        await govee.close()
        
    async def _setBrightness(self,bri) :
        govee = await Govee.create(self.api_key)
        devices, err = await govee.get_devices()
        success, err = await govee.set_brightness(self.device_id, bri)
        await govee.close()
                        
    async def _setColor(self,color) :
        govee = await Govee.create(self.api_key)
        devices, err = await govee.get_devices()
        success, err = await govee.set_color(self.device_id, color)
        await govee.close()
            
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 78},
               {'driver': 'GV1', 'value': 0, 'uom': 51},
               {'driver': 'GV6', 'value': 0, 'uom': 100},
               {'driver': 'GV7', 'value': 0, 'uom': 100},
               {'driver': 'GV8', 'value': 0, 'uom': 100}]

    id = 'GOVEE_LIGHT'
    commands = {
                    'DON': setOn,
                    'DOF': setOff,
                    'SET_BRI': setBrightness,
                    'SET_COLORID': setColor
                }

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('GoveeNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
