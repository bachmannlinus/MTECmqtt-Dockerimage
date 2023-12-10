#!/usr/bin/env python3
"""
MQTT server for M-TEC Energybutler reading modbus data
(c) 2023 by Christian Rödel 
"""

import logging
#FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
FORMAT = '[%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)

from config import cfg
from datetime import datetime, timedelta
import time
import signal
import mqtt
import MTECmodbusAPI
import hass_int

#----------------------------------
def signal_handler(signal_number, frame):
  global run_status
  logging.warning('Received Signal {}. Graceful shutdown initiated.'.format(signal_number))
  run_status = False

# =============================================
# MTEC Modbus read
# Helper to get list of registers to read
def get_register_list( category ):
  if category == "config":
    registers = [ '10000', '10011' ]
  elif category == "current":  
    registers = [ '10100', '10105', '11028', '11000', '30258', '11016', '30230', '33000' ] 
  elif category == "day":  
    registers = [ '31000', '31001', '31003', '31004', '31005']
  elif category == "total":  
    registers = [ '31102', '31104', '31108', '31110', '31112']
  else:
    logging.error("Unknown read category: {}".format(category))
    return None              
  return registers

# read data from MTEC modbus
def read_MTEC_data( api, category ):
  logging.info("Reading registers for category: {}".format(category))
  registers = get_register_list( category )
  now = datetime.now()
  data = api.read_modbus_data(registers=registers)
  pvdata = {}
  try:
    pvdata["api_date"] = now.strftime("%Y-%m-%d %H:%M:%S") # Local time of this server

    if category == "config":
      pvdata["serial_no"] = data["10000"]                   # Inverter serial number
      pvdata["firmware_version"] = data["10011"]            # Inverter firmware version

    elif category == "current":  
      pvdata["inverter_date"] = data["10100"]               # Time from inverter
      pvdata["inverter_status"] = data["10105"]             # Inverter status 
      pvdata["PV"] = data["11028"]                      # Current power flow from PV
      pvdata["grid"] = data["11000"]                    # Current power flow from/to grid
      pvdata["battery"] = data["30258"]                 # Current power flow from/to battery
      pvdata["inverter"] = data["11016"]                # Current power flow from/to inverter
      pvdata["backup"] = data["30230"]                  # Current backup power flow
      pvdata["consumption"] = data["11016"]["value"] - data["11000"]["value"]  # Current power consumption 
      pvdata["battery_SOC"] = data["33000"]           	# Current battery SOC

    elif category == "day":  
      pvdata["PV"] = data["31005"]                      # Energy generated by PV today
      pvdata["grid_feed"] = data["31000"]               # Energy feed to grid today
      pvdata["grid_purchase"] = data["31001"]           # Energy purchased from grid today
      pvdata["battery_charge"] = data["31003"]          # Energy charged to battery total
      pvdata["battery_discharge"] = data["31004"]       # Energy discharged from battery total
      pvdata["consumption"] = data["31005"]["value"] + data["31001"]["value"] + data["31004"]["value"] - data["31000"]["value"] - data["31003"]["value"]  # Current power consumption 
      pvdata["autarky_rate"] = 100*(1 - (data["31001"]["value"] / pvdata["consumption"])) if pvdata["consumption"]>0 else 0 
      pvdata["own_consumption_rate"] = 100*(1-data["31000"]["value"] / data["31005"]["value"]) if data["31005"]["value"]>0 else 0

    elif category == "total":  
      pvdata["PV"] = data["31112"]                      # Energy generated by PV total
      pvdata["grid_feed"] = data["31102"]               # Energy feed to grid total
      pvdata["grid_purchase"] = data["31104"]           # Energy purchased from grid total
      pvdata["battery_charge"] = data["31108"]          # Energy charged to battery total
      pvdata["battery_discharge"] = data["31110"]       # Energy discharged from battery total
      pvdata["consumption"] = data["31112"]["value"] + data["31104"]["value"] + data["31110"]["value"] - data["31102"]["value"] - data["31108"]["value"]  # Current power consumption 
      pvdata["autarky_rate"] = 100*(1 - (data["31104"]["value"] / pvdata["consumption"])) if pvdata["consumption"]>0 else 0
      pvdata["own_consumption_rate"] = 100*(1-data["31102"]["value"] / data["31112"]["value"]) if data["31112"]["value"]>0 else 0
  except Exception as e:
    logging.warning("Retrieved Modbus data is incomplete: {}".format(str(e)))
    return None
  return pvdata

# write data to MQTT
def write_to_MQTT( pvdata, base_topic ):
  for param, data in pvdata.items():
    topic = base_topic + param
    if isinstance(data, dict):
      if isinstance(data["value"], float):  
        payload = cfg['MQTT_FLOAT_FORMAT'].format( data["value"] )
      elif isinstance(data["value"], bool):  
        payload = "{:d}".format( data["value"] )
      else:
        payload = data["value"]
    else:   
      if isinstance(data, float):  
        payload = cfg['MQTT_FLOAT_FORMAT'].format( data )
      elif isinstance(data, bool):  
        payload = "{:d}".format( data )
      else:
        payload = data  
    mqtt.mqtt_publish( topic, payload )

#==========================================
def main():
  global run_status
  run_status = True 

  # Initialization
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGINT, signal_handler)
  if cfg['DEBUG'] == True:
    logging.getLogger().setLevel(logging.DEBUG)
  logging.info("Starting")

  next_read_config = datetime.now()
  next_read_day = datetime.now()
  next_read_total = datetime.now()
  topic_base = None
  
  if cfg["HASS_ENABLE"]:
    hass = hass_int.HassIntegration()
  else:
    hass = None
  
  mqttclient = mqtt.mqtt_start( hass )
  api = MTECmodbusAPI.MTECmodbusAPI()
  api.connect(ip_addr=cfg['MODBUS_IP'], port=cfg['MODBUS_PORT'], slave=cfg['MODBUS_SLAVE'])

  # Main loop - exit on signal only
  while run_status: 
    now = datetime.now()

    # Config
    if next_read_config <= now:
      pv_config = read_MTEC_data( api, "config" )
      if pv_config:
        topic_base = cfg['MQTT_TOPIC'] + '/' + pv_config["serial_no"]["value"] + '/'
        write_to_MQTT( pv_config, topic_base + 'config/' )
        next_read_config = datetime.now() + timedelta(hours=cfg['REFRESH_CONFIG_H'])
        if hass and not hass.is_initialized:
          hass.initialize( pv_config["serial_no"]["value"] )
      if not topic_base:
        logging.error("Cant retrieve initial config - retry in {}s".format( cfg['REFRESH_CURRENT_S'] ))
        time.sleep(cfg['REFRESH_CURRENT_S'])
        continue

    # Current    
    pvdata = read_MTEC_data( api, "current" )
    if pvdata:
      write_to_MQTT( pvdata, topic_base + 'current/' )

    # Day
    if next_read_day <= now:
      pvdata = read_MTEC_data( api, "day" )
      if pvdata:
        write_to_MQTT( pvdata, topic_base + 'day/' )
        next_read_day = datetime.now() + timedelta(minutes=cfg['REFRESH_DAY_M'])

    # Total
    if next_read_total <= now:
      pvdata = read_MTEC_data( api, "total" )
      if pvdata:
        write_to_MQTT( pvdata, topic_base + 'total/' )
        next_read_total = datetime.now() + timedelta(minutes=cfg['REFRESH_TOTAL_M'])

    logging.debug("Sleep {}s".format( cfg['REFRESH_CURRENT_S'] ))
    time.sleep(cfg['REFRESH_CURRENT_S'])

  # clean up
  if hass:
    hass.send_unregister_info()
  api.disconnect()
  mqtt.mqtt_stop(mqttclient)
  logging.info("Exiting")
 
#---------------------------------------------------
if __name__ == '__main__':
  main()
