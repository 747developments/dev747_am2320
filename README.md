# AM2320 sensor driver for Home Assistant used in Raspberry Pi
Custom component AM2320 sensor for Home Assistant

Copy the content of this directory to your homeassistant config directory:
  - example: ./config/custom_components/dev_747_AM2320/

##Requirements:
Enable I2C communication in Raspberry via raspi-config and install dependencies for handeling I2C communication in Python
```ruby
sudo apt-get update
sudo apt-get install python3-smbus python3-dev i2c-tools
```

##Parameters:
  - i2c_address: I2C address of AM2320 (typical 0x5C)
  - i2c_bus_num: I2C bus number (default raspberry = 1)
  - name: custom name of the sensor
  - monitored_conditions: temperature, humidity

Exaple configuration.yaml file:
```ruby
sensor:
  - platform: dev747_AM2320
    i2c_address: 0x5C
    i2c_bus_num: 25
    name: "AM2320_OUTDOOR"
    monitored_conditions:
      - temperature
      - humidity
    scan_interval: 2 
```
