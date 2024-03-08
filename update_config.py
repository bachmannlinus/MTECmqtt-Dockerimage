import os
import yaml
from datetime import datetime, timedelta

def update_config():
    # Laden der vorhandenen Konfigurationsdatei
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # Aktualisieren der Konfigurationsvariablen mit den Werten der Umgebungsvariablen
    for key, value in os.environ.items():
        if key in config:
            # Überprüfen, ob die Variable ein Integer-Wert ist
            if key.endswith(('_PORT', '_RETRIES', '_SLAVE', '_TIMEOUT', '_S', '_M')):
                try:
                    config[key] = int(value)
                except ValueError:
                    print(f"Error converting {key} value to integer.")
            # Überprüfen, ob die Variable ein Boolescher Wert ist
            elif key.startswith(('DEBUG', 'MQTT_DISABLE', 'ENABLE')):
                config[key] = value.lower() in ['true', 'yes', '1']
            # Variablen MQTT_LOGIN und MQTT_PASSWORD
            elif key == 'MQTT_LOGIN' or key == 'MQTT_PASSWORD':
                config[key] = value.strip('"')
            # Sonstige Variablen
            else:
                config[key] = str(value)

    # Schreiben der aktualisierten Konfiguration zurück in die Datei
    with open('config.yaml', 'w') as file:
        yaml.dump(config, file)

if __name__ == "__main__":
    update_config()
