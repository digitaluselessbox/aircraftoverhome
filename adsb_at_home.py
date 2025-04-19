import signal
import sys
import time
import socket
import select
import math
import json
import logging
import os

from utils import safe_int, safe_float, haversine

from logging.handlers import RotatingFileHandler
from logic.sbs_client import SBSClient
from logic.sbs_parser import SBSParser
from logic.aircraft_tracker import AircraftTracker
from logic.aircraft import Aircraft

ENVIRONTMENT = "DEVELOPMENT"

# Konfiguration
HOST = 'localhost'
PORT = 30003

# Standort des Hauses
HOME_LAT = 52.16136988133443
HOME_LON = 7.816642899449644

RADIUS_KM = 4
TTL_HOURS = 24  # Zeit in Stunden
TTL_SECONDS = TTL_HOURS * 3600
NEW_ENTRY_TTL_SECONDS = 3600

DUMP1090DATAFOLDER = "/usr/share/dump1090-mutability/html/data"
JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home.json"
ALLTIME_JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home_alltime.json"
LOG_DIRECTORY = "/var/log/dump1090-mutability"

if(ENVIRONTMENT == "DEVELOPMENT"):
    HOST = '192.168.178.121'
    DUMP1090DATAFOLDER = "./data"
    JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home.json"
    ALLTIME_JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home_alltime.json"
    LOG_DIRECTORY = "./log"


# Sicherstellen, dass das Verzeichnis für Logs existiert
os.makedirs(LOG_DIRECTORY, exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Standard-Logger für adsb_over_home.log
main_handler = RotatingFileHandler(f"{LOG_DIRECTORY}/adsb_over_home.log", maxBytes=512000, backupCount=10)
main_logger = logging.getLogger("main_logger")
main_logger.setLevel(logging.INFO)
main_logger.addHandler(main_handler)
main_handler.setFormatter(log_formatter)

# Debug-Logger für adsb_over_home_debug.log
debug_handler = RotatingFileHandler(f"{LOG_DIRECTORY}/adsb_over_home_debug.log", maxBytes=512000, backupCount=100)
debug_logger = logging.getLogger("debug_logger")
debug_logger.setLevel(logging.DEBUG)
debug_logger.addHandler(debug_handler)
debug_handler.setFormatter(log_formatter)

# Lines-Logger für adsb_over_home_lines.log
lines_handler = RotatingFileHandler(f"{LOG_DIRECTORY}/lines/adsb_over_home_lines.log", maxBytes=1024000, backupCount=100)
lines_logger = logging.getLogger("lines_logger")
lines_logger.setLevel(logging.DEBUG)
lines_logger.addHandler(lines_handler)
lines_handler.setFormatter(log_formatter)


# STRG+C-Handler
def signal_handler(sig, frame):
    main_logger.info("Skript wird beendet.")
    client.close()
    sys.exit(0)
    
signal.signal(signal.SIGINT, signal_handler)


tracker = AircraftTracker(
    json_path_current=JSON_FILE,
    json_path_alltime=ALLTIME_JSON_FILE,
    ttl_seconds=TTL_SECONDS,
    new_entry_ttl=NEW_ENTRY_TTL_SECONDS
)

client = SBSClient(HOST, PORT, logger=main_logger)
client.connect()

parser = SBSParser()

main_logger.info(f"Skript gestartet: {HOST}:{PORT}")

# laden der aircraft registration database json file and save it in a dictionary
with open(DUMP1090DATAFOLDER + "/database/aircraft_registrations.json", 'r') as file:
    aircraftRegistrationDB = json.load(file)

def is_valid_lat_lon( sbs_message ):
    # Prüft, ob die Latitude und Longitude gültig sind.
    
    return sbs_message.latitude is not None and sbs_message.longitude is not None and -90 <= sbs_message.latitude  <= 90 and -180 <= sbs_message.longitude <= 180


def is_valid_altitude( sbs_message ):
    # Prüft, ob die Höhe gültig ist.
    
    return sbs_message.altitude is not None and sbs_message.altitude >= 0

# Hauptschleife
buffer = ""
while True:
    try:
        #socketResponse = sock.recv(8192).decode('utf-8')
        lines = client.read_lines()
        debug_logger.debug(f"{len(lines)} Lines")

        if not lines:
            time.sleep(1)
            continue
        

        for line in lines:

            lines_logger.debug(f"Empfangene Zeile: {line}")

            current_time = time.time()

            sbs_message = parser.parse_line(line)
            
            if not sbs_message:
                continue  # Überspringe ungültige Nachrichten
            
            debug_logger.debug(f"Nachricht: {sbs_message}")

            try:
                if not is_valid_lat_lon( sbs_message ):
                    main_logger.warning(f"Ungültige Koordinaten für Flugzeug {sbs_message.icao}: lat={sbs_message.latitude}, lon={sbs_message.longitude}")
                    continue

                if not is_valid_altitude( sbs_message ):
                    main_logger.warning(f"Ungültige Höhe für Flugzeug {sbs_message.icao}: altitude={sbs_message.altitude}")
                    continue


                distance = haversine( HOME_LAT, HOME_LON, sbs_message.latitude, sbs_message.longitude )
                
                usedAction = "nothing"

                # Überprüfen, ob das Flugzeug innerhalb des definierten Radius ist
                if distance >= RADIUS_KM:
                    continue


                registration = aircraftRegistrationDB.get(sbs_message.icao.upper())  # `.get()` gibt None zurück, falls der Key nicht existiert
                
                if registration:
                    main_logger.info(f"Registration for {sbs_message.icao}: {registration}")
                else:
                    main_logger.warning(f"Key {sbs_message.icao} not found in JSON data.")

                aircraft = Aircraft(
                    hex = sbs_message.icao,
                    registration = registration,
                    altitude = sbs_message.altitude,
                    lat = sbs_message.latitude,
                    lon = sbs_message.longitude,
                    timestamp = sbs_message.timestamp
                )
                aircraft.calculate_distance(HOME_LAT, HOME_LON)
                

                relevant_entries = tracker.get_existing_entries(aircraft.hex)
                
                if not relevant_entries or tracker.should_add_new(relevant_entries, current_time):
                    usedAction = "new aircraft"
                    tracker.add_aircraft( aircraft )
                elif relevant_entries and not tracker.should_add_new(relevant_entries, current_time):
                      
                    # Aktualisiere den jüngsten Eintrag bei sinkender Höhe
                    latest_entry = max( relevant_entries, key = lambda x: x['last_seen'] )
                    
                    # aircraft nur aktualisieren, wenn entfernung niedriger ist als die gespeichert Entfernung
                    if aircraft.distance < latest_entry.distance:
                        usedAction = "update aircraft"
                        tracker.update_aircraft(latest_entry, aircraft)
                #else:
                    # so nothing to do, aircraft is already in the list


                # little debugging
                if usedAction != "nothing":
                    # logge das aircraft
                    main_logger.info(f"Detected aircraft: {aircraft}")
                    main_logger.info(f"********************************************************************************")
                    main_logger.info(f"Action: {usedAction}")
                    main_logger.info(f"Aircraft: {aircraft}")
              
            except ValueError as e:
                main_logger.error(f"Fehler beim Verarbeiten der SBSMessage {sbs_message}: {e}")
    
        
        # veraltete Flugzeuge separieren und zum Archivieren speichern
        tracker.cleanup_old(current_time)

        # Speichern in der gewünschten JSON-Struktur
        try:
            tracker.save_all()            
        except IOError as e:
            main_logger.error(f"Fehler beim Speichern der JSON-Datei: {e}")
        
        
        time.sleep(5)

    except BlockingIOError:
        time.sleep(1)

    except Exception as e:
        main_logger.error(f"Unerwarteter Fehler: {e}")
