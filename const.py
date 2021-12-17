"""CONSTANTS"""

DEFAULT_NAME            = "I2C Sensor"
SENSOR_TEMP             = "temperature"
SENSOR_HUMID            = "humidity"
DEFAULT_I2C_ADDRESS     = "0x5C"
DEFAULT_I2C_BUS         = 1
CRC_VAL                 = 0xFFFF
DEFAULT_EMPTY_RAW_DATA  = [None, None, None, None, None, None, None, None]

_SENSOR_TYPES = {
    "temperature":  ("Temperature",     "",     "mdi:thermometer",      "°C"),
    "humidity":     ("Humidity",        "",     "mdi:water-percent",    "%"),
}
