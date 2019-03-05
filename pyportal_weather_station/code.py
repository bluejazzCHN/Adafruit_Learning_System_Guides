import time
import board
import neopixel
import busio
import analogio
from simpleio import map_range
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager

# sensor libs
import adafruit_veml6075
import adafruit_sgp30
import adafruit_bme280

# weathermeter_helper file
import weathermeter_helper


# anemometer defaults
anemometer_min_volts = 0.4
anemometer_max_volts = 2.0
min_wind_speed = 0.0
max_wind_speed = 32.4

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# PyPortal ESP32 Setup
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
ADAFRUIT_IO_USER = secrets['adafruit_io_user']
ADAFRUIT_IO_KEY = secrets['adafruit_io_key']

# create an i2c object
i2c = busio.I2C(board.SCL, board.SDA)

# instantiate the sensor objects
veml = adafruit_veml6075.VEML6075(i2c, integration_time=100)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

# init. the graphics helper
gfx = weathermeter_helper.WeatherMeter_GFX()

# rate at which to refresh the pyportal and sensors, in seconds
PYPORTAL_REFRESH = 15

# initialize the Adafruit IO helper
io_helper = weathermeter_helper.WeatherMeter_IO(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

# init. the ADC
adc = analogio.AnalogIn(board.D4)

def adc_to_wind_speed(val):
    # converts adc value to wind speed, in m/s 
    voltage_val = val / 65535 * 3.3
    return map_range(adc_value, 0.4, 2, 0, 32.4)

while True:
    try:
        # Get uv index from veml6075
        uv_index = veml.uv_index
        uv_index = round(uv_index, 3)
        print('UV Index: ', uv_index)

        # Get eco2, tvoc from sgp30
        eCO2, TVOC = sgp30.iaq_measure()
        sgp_data = [eCO2, TVOC]

        # Store bme280 data as a list
        bme280_data = [bme280.temperature, bme280.humidity, bme280.pressure, bme280.altitude]

        # Get wind speed
        wind_speed = adc_to_wind_speed(adc.value)
        # Perform sensor read, display data and send to IO
        print('displaying sensor data...')
        gfx.display_data(uv_index, bme280_data, sgp_data, io_helper)
        print('sensor data displayed!')
    except (ValueError, RuntimeError) as e: # ESP32SPI Failure
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)