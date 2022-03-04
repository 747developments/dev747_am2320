from __future__ import annotations
"""Driver for Home Assistant to handle AM2320 sensor."""
import logging
import os
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

from .const import (
    DEFAULT_NAME,
    SENSOR_TEMP,
    SENSOR_HUMID,
    DEFAULT_I2C_ADDRESS,
    DEFAULT_I2C_BUS,
    CRC_VAL,
    DEFAULT_EMPTY_RAW_DATA,
    _SENSOR_TYPES
)

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

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""

    # if discovery_info is None:
        # return
    i2c_address = config.get(CONF_I2C_ADDRESS)
    i2c_bus_num = config.get(CONF_I2C_BUS_NUM)
    name = config.get(CONF_NAME)
    for monitored_condition in config[CONF_MONITORED_CONDITIONS]:
        add_entities([AM2320(name, i2c_address, i2c_bus_num, monitored_condition)])
        time.sleep(0.01)

class AM2320(SensorEntity):
    """ AM2320."""

    def __init__(self, name, i2c_address, i2c_bus_num, monitored_condition):
        """Initialize the sensor."""
        self.CRC = CRC_VAL
        self._monitored_condition = monitored_condition
        self._name = name
        self._state = None
        self.raw_data = DEFAULT_EMPTY_RAW_DATA
        self.non_receive_counter = 0
 
        self._i2c_bus_num = i2c_bus_num
        self._i2c_address = i2c_address        
        self._i2c_bus = smbus.SMBus(self._i2c_bus_num)  
        
        return
        
    def combine_bytes(self, msb, lsb):
        """Combine bytes."""
        return ((msb << 8) | lsb)
        
    def calc_crc16(self, data):
        """Calculate CRC."""
        crc = CRC_VAL
        for x in data:
            crc ^= x
            for i in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
        
    def wake_up_sensor(self):
        """Wake up sensor."""
        try:
            self._i2c_bus.write_byte(self._i2c_address, 0x00)
            time.sleep(0.001) #Wait at least 0.8ms, at most 3ms
        except:
            pass
        return
    
    def read_measurements_raw_data(self):
        """Read data from I2C bus."""
        self._i2c_bus.write_i2c_block_data(self._i2c_address, 0x03, [0x00, 0x04]) 
        time.sleep(0.005) #Wait at least 1.5ms for result
        self.raw_data = self._i2c_bus.read_i2c_block_data(self._i2c_address, 0, 8)
        return
        
    def compute_temperature(self): 
        """Get temperature."""
        temperature = self.combine_bytes(self.raw_data[4], self.raw_data[5])
        if temperature & 0x8000:
            temperature = -(temperature & 0x7FFF)
        temperature /= 10.0
            
        return temperature
        
    def compute_humidity(self):
        """Get humidity."""
        humidity = self.combine_bytes(self.raw_data[2], self.raw_data[3]) / 10.0
        return humidity
            
    def get_data(self):
        """Get data from sensor."""
        self.CRC = CRC_VAL
        self.raw_data = DEFAULT_EMPTY_RAW_DATA
        self.wake_up_sensor()
        
        try:
            self.read_measurements_raw_data()
            
            if ((self.raw_data[0] != 0x03) or (self.raw_data[1] != 0x04)):
                _LOGGER.error("First 2 bytes received mismatch A2320 %d - %s-%s" % (self.non_receive_counter, self._name, self._monitored_condition))
            
            else:
                crc = self.calc_crc16(self.raw_data[:6]) 
                if crc == self.combine_bytes(self.raw_data[-1], self.raw_data[-2]):
                    if self._monitored_condition == SENSOR_TEMP:                
                        self._state = self.compute_temperature()                
                    else:                
                        self._state = self.compute_humidity()                
                else:
                    _LOGGER.error("CRC failed A2320 %d - %s-%s" % (self.non_receive_counter, self._name, self._monitored_condition))
                
            self.non_receive_counter = 0
            
        except Exception as ex:
            self.non_receive_counter += 1
            if(self.non_receive_counter >= 10):
                _LOGGER.error("Error retrieving A2320 data %d - %s-%s: %s" % (self.non_receive_counter, self._name, self._monitored_condition, ex))
                self.non_receive_counter = 0
                self._state = None
            time.sleep(0.1)
       
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

    def update(self):
        self.get_data()

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return _SENSOR_TYPES[self._monitored_condition][3]