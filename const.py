"""Constants for Hisense VRF integration."""

DOMAIN = "hisense_vrf"
PLATFORMS = ["climate"]

# API
API_BASE_AUTH = "https://auth-gateway.hijuconn.com/"
API_BASE_DEVICE = "https://dm-gateway.hijuconn.com/"
API_BASE_SHADOW = "https://shadow-gateway.hijuconn.com/"
API_BASE_HOME = "https://lc-gateway.hijuconn.com/"

# App credentials (from APK)
APP_KEY = "1184507461"
APP_SECRET = "mj63isp9gr2oqhse9qsk0pg1meb88rdl"
API_VERSION = "5.0"
LANGUAGE_ID = "1"
SALT = "D9519A4B756946F081B7BB5B5E8D1197"

RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyyWrNG6q475HIHu7sMVu
vHof6vlgPeixmxa4EL/UsvVvHPz33NnWoQetQqit9TBNzUjMXw0KlY9PXM4iqHUU
U+dSyNDq1jZWIiJ2C2FccppswJtIKL3NRMFvT9PFh6NlP/4FUcQKojgKFbF7Kacc
JPKYHlwaO7qgoIjLxAHlSOXGpucJcOkPzT2EqsSVnW8sn8kenvNmghXDayhgxsh6
AyxK4kehJplEnmX/iYCfNoFXknGcLqFWYccgBz3fybvx30C/0IgU1980L8QsUAv5
esZmN8ugnbRgLRxKRlkQQLxQAiZMZdKTAx665YflT3YMHJvEFE8c2XFgoxHzSMc4
BwIDAQAB
-----END PUBLIC KEY-----"""

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_HOME_ID = "home_id"
CONF_WIFI_ID = "wifi_id"

# Update interval in seconds
UPDATE_INTERVAL = 30

# Device modes (boolean flag properties)
MODE_REFRIGERATION = "modeRefrigeration"
MODE_HEATING = "modeHeating"
MODE_AUTOMATIC = "modeAutomatic"
MODE_DEHUMIDIFICATION = "modeDeHumidification"
MODE_SUPPLY_AIR = "modeSupplyAir"

# Fan speed properties
FAN_HIGH = "setHighWind"
FAN_MEDIUM = "setMediumWind"
FAN_LOW = "setLowWind"
FAN_SUPER_HIGH = "setSuperHighWind"
FAN_QUIET = "setQuietSound"
FAN_AUTO = "isAutoAirVolume"

# Temperature
PROP_SET_TEMP = "setTemp"
PROP_ROOM_TEMP = "suctionAirTemp"
PROP_POWER = "Y_K_Q_control"
PROP_OPERATING_STATE = "actualOperatingState"
TEMP_MIN = 16
TEMP_MAX = 32
