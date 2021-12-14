import pyipmi.interfaces
from pyipmi.errors import IpmiTimeoutError

import settings
import paho.mqtt.client as mqtt
import time
import sys
import json

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        global Connected  # Use global variable
        Connected = True  # Signal connection
    else:
        print("Connection to MQTT broker failed")

def publish_sdr_to_mqtt(entityId, entityNumber, entityName, enitityValue):
    try:
        stringData = {"id": entityId, "number": entityNumber, "name": entityName, "value":  enitityValue}
        jsonData = json.dumps(stringData)

        topic = mqttPrefix + str(entityId) + "." + str(entityNumber)

        mqttClient.publish(topic, jsonData, 0, False)
    except Exception as e:
        print('Failed to publish to MQTT broker:', e)

def get_sdr_entities(ipmi):
    iter_fct = None

    device_id = ipmi.get_device_id()
    if device_id.supports_function('sdr_repository'):
        iter_fct = ipmi.sdr_repository_entries
    elif device_id.supports_function('sensor'):
        iter_fct = ipmi.device_sdr_entries

    for sdrSensor in iter_fct():
        try:
            sdrId = "n/a"
            sdrDeviceString = "n/a"
            number = None
            value = None
            states = None

            if sdrSensor.type is pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD:
                (value, states) = ipmi.get_sensor_reading(sdrSensor.number)
                number = sdrSensor.number
                if value is not None:
                    value = sdrSensor.convert_sensor_raw_to_value(value)

            elif sdrSensor.type is pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD:
                (value, states) = ipmi.get_sensor_reading(sdrSensor.number)
                number = sdrSensor.number
                state = ipmi.get
            
            if sdrSensor.type is not pyipmi.sdr.SDR_TYPE_OEM_SENSOR_RECORD:
                sdrDeviceString = str(sdrSensor.device_id_string).removeprefix("b'").removesuffix("'") # strip b'xxxxx'
                if (sdrSensor.entity_id is not None and sdrSensor.entity_instance is not None):
                    sdrId = str(sdrSensor.entity_id) + "." + str(sdrSensor.entity_instance);
            
            publish_sdr_to_mqtt(sdrId, number, sdrDeviceString, value)

        except pyipmi.errors.CompletionCodeError as e:
            if sdrSensor.type in (pyipmi.sdr.SDR_TYPE_COMPACT_SENSOR_RECORD, pyipmi.sdr.SDR_TYPE_FULL_SENSOR_RECORD):
                print('0x{:04x} | {:3d} | {:18s} | ERR: CC=0x{:02x}'.format(
                      sdrSensor.id,
                      sdrSensor.number,
                      sdrSensor.device_id_string,
                      e.cc))


Connected = False

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    
    interface = pyipmi.interfaces.create_interface(interface='rmcp',
                                                   slave_address=0x81,
                                                   host_target_address=0x20,
                                                   keep_alive_interval=1)

    ipmi = pyipmi.create_connection(interface)
    print(f'Setting IPMI host to "{settings.IPMI_HOST}" on port 623...')
    ipmi.session.set_session_type_rmcp(host=settings.IPMI_HOST, port=623)
    ipmi.session.set_auth_type_user(username=settings.IPMI_USERNAME, password=settings.IPMI_PASSWORD)
    ipmi.target = pyipmi.Target(ipmb_address=0x20)
    try:
        print('Connecting to IPMI host...')
        ipmi.session.establish()
    except Exception as e:
        sys.exit('Cannot connect to IPMI host')

    mqttPrefix = "ipmi2mqtt/" + settings.MQTT_TOPIC_PREFIX + '/'

    mqttClient = mqtt.Client()
    if (settings.MQTT_USERNAME):
        print('Setting MQTT credentials...')
        mqttClient.username_pw_set(settings.MQTT_USERNAME, password=settings.MQTT_PASSWORD)  # set username and password

    mqttClient.on_connect = on_connect
    print(f'Connecting to MQTT at "{settings.MQTT_HOST}" on port {settings.MQTT_PORT}...')
    mqttClient.connect(settings.MQTT_HOST, int(settings.MQTT_PORT))
    mqttClient.loop_start()

    while Connected != True:  # Wait for connection
        time.sleep(0.1)
        
    device_id = ipmi.get_device_id()

    print("--- Printing Device ID ---")
    functions = (
            ('SENSOR', 'Sensor Device', 11),
            ('SDR_REPOSITORY', 'SDR Repository Device', 3),
            ('SEL', 'SEL Device', 14),
            ('FRU_INVENTORY', 'FRU Inventory Device', 4),
            ('IPMB_EVENT_RECEIVER', 'IPMB Event Receiver', 5),
            ('IPMB_EVENT_GENERATOR', 'IPMB Event Generator', 4),
            ('BRIDGE', 'Bridge', 18),
            ('CHASSIS', 'Chassis Device', 10))
    ChkBox=['[ ]','[X]']
    print('''
    Device ID:                  %(device_id)s
    Provides Device SDRs:       %(provides_sdrs)s
    Device Revision:            %(revision)s
    Device Available:           %(available)d
    Firmware Revision:          %(fw_revision)s
    IPMI Version:               %(ipmi_version)s
    Manufacturer ID:            %(manufacturer_id)d (0x%(manufacturer_id)04x)
    Product ID:                 %(product_id)d (0x%(product_id)04x)
    Aux Firmware Rev Info:      %(aux)s
    Additional Device Support: '''[1:-1] % device_id.__dict__)
    for n, s, l in functions:
        if device_id.supports_function(n):
            print('        %s%s%s' % (s,l*' ',ChkBox[1]))
        else:
            print('        %s%s%s' % (s,l*' ',ChkBox[0]))
    print('Getting SDR entities and publishing to MQTT...')
            
    while True:
        try:
            get_sdr_entities(ipmi);
            print('Published SDR entities to MQTT...')
            
        except Exception as e:
            print('Cannot read ipmi sensors:', e)
            ipmi.session.close()
            print('IPMI disconnected')

            mqttClient.disconnect()
            mqttClient.loop_stop()
            print('MQTT disconnected')

        time.sleep(settings.IPMI_SCAN_INTERVAL)