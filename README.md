bachmannlinus/MTECmqtt-Dockerimage

# MTECmqtt-Dockerimage for MTEC-Energybutler

## Introduction
Thanks to the MTECmqtt-Project from croedel (https://github.com/croedel/MTECmqtt) I have made an Dockerimage that runs the pythonscripts from the Project.

## Pull Image
```
docker pull bachmannlinus/mtecmqtt:latest
```

## Configuration
You have to set the Ports `5743`, as well as your desired MQTT-Port (most of the time `1883`) open when you compose your image.

## Environmental variables
| Environmental variable   | Example-value        |
|--------------------------|----------------------|
| MODBUS_IP                | espressif.fritz.box  |
| MODBUS_PORT              | 5743                 |
| MODBUS_SLAVE             | 252                  |
| MODBUS_TIMEOUT           | 5                    |
| MODBUS_RETRIES           | 3                    |
| MODBUS_FRAMER            | rtu                  |
| MQTT_DISABLE             | False                |
| MQTT_SERVER              | localhost            |
| MQTT_PORT                | 1883                 |
| MQTT_LOGIN               | "MQTT"                  |
| MQTT_PASSWORD            | "MQTT"                   |
| MQTT_TOPIC               | MTEC                 |
| MQTT_FLOAT_FORMAT        | "{:.3f}"             |
| REFRESH_NOW_S            | 10                   |
| REFRESH_NOWEXT_S         | 30                   |
| REFRESH_DAY_M            | 5                    |
| REFRESH_TOTAL_M          | 5                    |
| REFRESH_CONFIG_M         | 60                   |
| ENABLE_GRID_DATA         | False                |
| ENABLE_INVERTER_DATA     | False                |
| ENABLE_BACKUP_DATA       | False                |
| ENABLE_BATTERY_DATA      | False                |
| ENABLE_PV_DATA           | False                |
| HASS_ENABLE              | False                |
| HASS_BASE_TOPIC          | homeassistant        |
| HASS_BIRTH_GRACETIME     | 15                   |
| DEBUG                    | False                |

