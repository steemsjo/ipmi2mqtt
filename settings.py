from dotenv import load_dotenv
import os
load_dotenv()

try:
    IPMI_HOST = os.getenv('IPMI_HOST', 'not set')
    IPMI_USERNAME = os.getenv('IPMI_USERNAME', 'not set')
    IPMI_PASSWORD = os.getenv('IPMI_PASSWORD', 'not set')
    IPMI_SCAN_INTERVAL = int(os.getenv('IPMI_SCAN_INTERVAL', 5))

    MQTT_HOST = os.getenv('MQTT_HOST', 'not set')
    MQTT_PORT = os.getenv('MQTT_PORT', 1883)
    MQTT_USERNAME = os.getenv('MQTT_USERNAME')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
    MQTT_TOPIC_PREFIX = os.getenv('MQTT_TOPIC_PREFIX', IPMI_HOST).rstrip("/")
except Exception as e:
    print('Cannot read environment variables:', e)