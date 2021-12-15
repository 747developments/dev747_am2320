from __future__ import annotations

__version__ = '1.0.0'

import logging
import os
# import fcntl
import time
import voluptuous as vol
import smbus

from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT, SensorEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.components.group import expand_entity_ids
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_BATTERY_LEVEL,
    CONF_DEVICES,
    CONF_TEMPERATURE_UNIT,
    CONF_NAME,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    PERCENTAGE,
    CONF_SENSORS,
    CONF_MONITORED_CONDITIONS
)

# Attributes
I2C_SLAVE_ADDR          = 0x0703

DOMAIN                  = "dev_747_am2320"
DEFAULT_NAME            = "I2C Sensor"
SENSOR_TEMP             = "temperature"
SENSOR_HUMID            = "humidity"

_SENSOR_TYPES = {
    "temperature":  ("Temperature",     "",     "mdi:thermometer",      "°C"),
    "humidity":     ("Humidity",        "",     "mdi:water-percent",    "%"),
}

DEFAULT_I2C_ADDRESS     = "0x5C"
DEFAULT_I2C_BUS         = 1
CRC_VAL                 = 0xFFFF

CONF_I2C_ADDRESS        = "i2c_address"
CONF_I2C_BUS_NUM        = "i2c_bus_num"
CONF_NAME               = "name"

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_I2C_ADDRESS, default=DEFAULT_I2C_ADDRESS): cv.positive_int,
    vol.Required(CONF_I2C_BUS_NUM, default=DEFAULT_I2C_BUS): cv.positive_int,
    vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS): vol.All(
            cv.ensure_list, [vol.In(_SENSOR_TYPES)]
        ),
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""

    # if discovery_info is None:
        # return
    i2c_address = config.get(CONF_I2C_ADDRESS)
    i2c_bus_num = config.get(CONF_I2C_BUS_NUM)
    name = config.get(CONF_NAME)
    #_LOGGER.warning(config[CONF_MONITORED_CONDITIONS])
    for monitored_condition in config[CONF_MONITORED_CONDITIONS]:
        async_add_entities([AM2320(name, i2c_address, i2c_bus_num, monitored_condition)])

class AM2320(SensorEntity):
    """ AM2320."""

    def __init__(self, name, i2c_address, i2c_bus_num, monitored_condition):
        """Initialize the sensor."""
        self.CRC = CRC_VAL
        self._monitored_condition = monitored_condition
        self._name = name
        self._state = None
        self.raw_data = None
 
        self._i2c_bus_num = i2c_bus_num
        self._i2c_address = i2c_address        
        self._i2c_bus = smbus.SMBus(self._i2c_bus_num)  
        
        # self.fd = os.open("/dev/i2c-%d" % (self._i2c_bus_num), os.O_RDWR)
        # fcntl.ioctl(self.fd, I2C_SLAVE_ADDR, self._i2c_address)
        
        return
    
    def wake_up_sensor(self):
        try:
            self._i2c_bus.write_byte(self._i2c_address, 0x00)
            time.sleep(0.001)
        except:
            pass
        return
    
    def read_measurements_raw_data(self): 
        self._i2c_bus.write_i2c_block_data(self._i2c_address, 0x03, [0x00, 0x04]) 
        #os.write(self.fd, b'\x03\x00\x04')
        time.sleep(0.002)
        self.raw_data = self._i2c_bus.read_i2c_block_data(self._i2c_address, 0, 8)
        #self.raw_data = bytearray(os.read(self.fd, 8))
        return
        
    def compute_temperature(self):  
        temperature = self._combine_bytes(self.raw_data[4], self.raw_data[5])
        if temperature & 0x8000:
            temperature = -(temperature & 0x7FFF)
        temperature /= 10.0
            
        return temperature
        
    def compute_humidity(self):
        humidity = self._combine_bytes(self.raw_data[2], self.raw_data[3]) / 10.0
        return humidity
    
    @staticmethod
    def _calc_crc16(data):
        crc = CRC_VAL
        for x in data:
            crc = crc ^ x
            for bit in range(0, 8):
                if (crc & 0x0001) == 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def _combine_bytes(msb, lsb):
        return msb << 8 | lsb
         
    def get_data(self):
        #Reset the CRC variable
        self.CRC = CRC_VAL
        
        self.wake_up_sensor()
        
        try:
            self.read_measurements_raw_data()
            
            if ((self.raw_data[0] != 0x03) or (self.raw_data[1] != 0x04)):
                raise Exception("AM2320 - First two read bytes mismatched")
            
            # CRC check
            if self._calc_crc16(self.raw_data[0:6]) != self._combine_bytes(self.raw_data[7], self.raw_data[6]):
                raise Exception("AM2320 - CRC failed")
                        
            #_LOGGER.warning(self._monitored_condition == SENSOR_TEMP)
            if self._monitored_condition == SENSOR_TEMP:                
                self._state = self.compute_temperature()                
            else:                
                self._state = self.compute_humidity()
                    
        except Exception as ex:
            _LOGGER.error("Error retrieving A2320 data: %s" % (ex))
       
    @property
    def name(self):
        """Return the name of the entity."""
        return "{} - {}".format(self._name, _SENSOR_TYPES[self._monitored_condition][0])
        
    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return _SENSOR_TYPES[self._monitored_condition][2]

    async def async_update(self):
        self.get_data()

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return _SENSOR_TYPES[self._monitored_condition][3]