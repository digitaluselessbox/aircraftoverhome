import signal
import sys
import time
import socket
import select
import math
import json
import paho.mqtt.client as mqtt
import logging
from logging.handlers import RotatingFileHandler

# Logging einrichten
# handler = RotatingFileHandler("/usr/share/dump1090-mutability/logs/adsb.log", maxBytes=250000, backupCount=5)
handler = RotatingFileHandler("/var/log/dump1090-mutability/adsb.log", maxBytes=250000, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[handler]
)
logging.info("Skript gestartet")

try:


    # Konfiguration
    HOST = 'localhost'
    PORT = 30003
    MQTT_BROKER_IP = '192.168.178.103'
    MQTT_BROKER_PORT = 1883
    MQTT_BROKER_USERNAME = "dump1o090fromfr24"
    MQTT_BROKER_PASSWORD = "dump1090fromfr24"
    MQTT_TOPIC = 'adsb/flugzeuge'

    # Standort des Hauses
    HOME_LAT = 52.16136988133443
    HOME_LON = 7.816642899449644

    RADIUS_KM = 400
    TTL = 60  # Zeit bis Flugzeuge als veraltet gelten

    # Distanzberechnung
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # STRG+C-Handler
    def signal_handler(sig, frame):
        logging.info("Skript wird beendet.")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        sock.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # MQTT-Client konfigurieren
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_BROKER_USERNAME, MQTT_BROKER_PASSWORD)
    mqtt_client.connect(MQTT_BROKER_IP, MQTT_BROKER_PORT)
    mqtt_client.loop_start()

    # Verbindung zu Dump1090
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex((HOST, PORT))
    ready_to_read, ready_to_write, in_error = select.select([], [sock], [], 5)
    if not ready_to_write:
        logging.error("Verbindung zum dump1090-Server fehlgeschlagen.")
        sys.exit(1)
    logging.info("Verbindung erfolgreich hergestellt.")

    detected_aircraft = {}

    # Hauptschleife
    while True:
        try:
            data = sock.recv(8192).decode('utf-8')
            logging.info(data.splitlines())
            if data:
                for line in data.splitlines():
                    fields = line.split(',')
                    if len(fields) > 10 and fields[0] == 'MSG' and fields[1] == '3' and len(fields) >= 16:
                        try:
                            icao = fields[4]
                            lat = float(fields[14])
                            lon = float(fields[15])
                            altitude = fields[11]
                            distance = haversine(HOME_LAT, HOME_LON, lat, lon)
                            
                            if distance <= RADIUS_KM:
                                current_time = time.time()
                                detected_aircraft[icao] = {
                                    "icao": icao,
                                    "altitude": altitude,
                                    "latitude": lat,
                                    "longitude": lon,
                                    "distance_km": distance,
                                    "last_seen": current_time
                                }
                        except ValueError as e:
                            logging.error(f"Fehler beim Verarbeiten der Nachricht {fields}: {e}")

            # Veraltete Flugzeuge entfernen
            current_time = time.time()
            detected_aircraft = {
                icao: data
                for icao, data in detected_aircraft.items()
                if current_time - data["last_seen"] <= TTL
            }

            # Flugzeuge senden
            payload = {
                "aircraft": list(detected_aircraft.values())
            }
            mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
            logging.info(f"Gesendete Flugzeuge: {len(detected_aircraft)}")

            time.sleep(5)

        except BlockingIOError:
            time.sleep(1)

        except Exception as e:
            logging.error(f"Unerwarteter Fehler: {e}")

except Exception as e:
        logging.error(f"Unerwarteter Fehler: {e}")