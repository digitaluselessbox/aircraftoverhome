import signal
import sys
import time
import socket
import select
import math
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from collections import namedtuple
from utils import safe_int, safe_float, haversine

ENVIRONTMENT = "DEVELOPMENT"

# Konfiguration
HOST = 'localhost'
PORT = 30003

# Standort des Hauses
HOME_LAT = 52.16136988133443
HOME_LON = 7.816642899449644

RADIUS_KM = 2
TTL_HOURS = 24  # Zeit in Stunden
TTL_SECONDS = TTL_HOURS * 3600
NEW_ENTRY_TTL_SECONDS = 3600

DUMP1090DATAFOLDER = "/usr/share/dump1090-mutability/html/data"
JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home.json"
ALLTIME_JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home_alltime.json"
LOG_DIRECTORY = "/var/log/dump1090-mutability"

if(ENVIRONTMENT == "DEVELOPMENT"):
    HOST = '192.168.178.115'
    DUMP1090DATAFOLDER = "./data"
    JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home.json"
    ALLTIME_JSON_FILE = DUMP1090DATAFOLDER + "/aircraft_over_home_alltime.json"
    LOG_DIRECTORY = "./log"


# Definition des NamedTuple für SBS-Daten
SBSMessage = namedtuple('SBSMessage', [
    'message_type',     # Typ der Nachricht (z. B. MSG)
    'transmission_type',# Übertragungstyp (z. B. 3 für Position)
    'icao',             # HexIdent des Flugzeugs
    'altitude',         # Höhe in Fuß
    'latitude',         # Breitengrad
    'longitude',        # Längengrad
    'timestamp'         # Zeitstempel der Nachricht
])

# Definition des NamedTuple für Flugzeugdaten
Aircraft = namedtuple('Aircraft', [
    'hex', 
    'registration',
    'altitude', 
    'distance',
    'lat', 
    'lon', 
    'seen', 
    'last_seen'
])

# Sicherstellen, dass das Verzeichnis für Logs existiert
os.makedirs(LOG_DIRECTORY, exist_ok=True)

# Logging einrichten
# handler = RotatingFileHandler(f"{LOG_DIRECTORY}/adsb_over_home.log", maxBytes=512000, backupCount=10)
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[handler]
# )

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
    logging.info("Skript wird beendet.")
    sock.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def parse_sbs_message(line):
    # Parst eine Zeile im SBS-BaseStation-Format und gibt ein SBSMessage zurück.
    # Es werden nur Nachrichten des Typs MSG und mit Übertragungstyp 3 verarbeitet.

    fields = line.split(',')

    try:
       
        if len(fields) < 10:
            raise ValueError(f"Unvollständige SBS-Nachricht(<10).")
        
        message_type = fields[0] if len(fields) > 0 else None
        transmission_type = safe_int(fields[1]) if len(fields) > 1 else None
        
        if message_type != 'MSG' or transmission_type != 3:
            return None
    

        if message_type == 'MSG' and len(fields) < 22:
            raise ValueError(f"Unvollständige SBS-Nachricht(MSG, <22).")
        

        icao = fields[4] if len(fields) > 4 else None
        altitude = safe_int(fields[11]) if len(fields) > 11 else None
        latitude = safe_float(fields[14]) if len(fields) > 14 else None
        longitude = safe_float(fields[15]) if len(fields) > 15 else None

        # logging.info(f"ICAO: {icao}, Altitude: {altitude}, Latitude: {latitude}, Longitude: {longitude}")

        if not icao:
            raise ValueError("Fehlende ICAO-Adresse.")
                     

        return SBSMessage(
            message_type = message_type,
            transmission_type = transmission_type,
            icao = icao,
            altitude = altitude,
            latitude = latitude,
            longitude = longitude,
            timestamp = time.time()
        )
    
    except (IndexError, ValueError) as e:
        logging.error(f"Ungültige SBS-Nachricht: {line}, Fehler: {e}")
        return None


main_logger.info(f"Skript gestartet: {HOST}:{PORT}")


# Socket Verbindung zu Dump1090 herstellen
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # Erhöhe den Empfangspuffer
sock.setblocking(False)
sock.connect_ex((HOST, PORT))
ready_to_read, ready_to_write, in_error = select.select([], [sock], [], 5)
if not ready_to_write:
    main_logger.error("Verbindung zum dump1090-Server fehlgeschlagen.")
    sys.exit(1)
main_logger.info("Verbindung erfolgreich hergestellt.")

# laden der aircraft registration database json file and save it in a dictionary
with open(DUMP1090DATAFOLDER + "/database/aircraft_registrations.json", 'r') as file:
    aircraftRegistrationDB = json.load(file)
    

def load_aircraft_json(filepath):
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"now": time.time(), "aircraft": []}


def save_aircraft_json(filepath, data):
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)


def add_aircraft(detected_aircraft, aircraft, current_time):
    """
    Fügt ein neues Flugzeug in die Liste detected_aircraft hinzu.
    """
    main_logger.info(f"Neues Flugzeug gesichtet: ICAO/HEX {aircraft.hex}")
    detected_aircraft.append({
        "hex": aircraft.hex,
        "registration": aircraft.registration,
        "altitude": aircraft.altitude,
        "distance": aircraft.distance,
        "lat": aircraft.lat,
        "lon": aircraft.lon,
        "seen": 1,
        "last_seen": current_time
    })


def update_aircraft(entry, aircraft, current_time):
    # Aktualisiert die Daten eines bestehenden Flugzeugs, falls die Bedingungen erfüllt sind.

    # main_logger.info(f"Flugzeug aktualisiert: ICAO/HEX { entry['hex'] }")

    entry.update({
        "altitude": aircraft.altitude,
        "distance": aircraft.distance,
        "lat": aircraft.lat,
        "lon": aircraft.lon,
        "seen": 1,
        "last_seen": current_time
    })

def is_valid_lat_lon( sbs_message ):
    # Prüft, ob die Latitude und Longitude gültig sind.
    
    return sbs_message.latitude is not None and sbs_message.longitude is not None and -90 <= sbs_message.latitude  <= 90 and -180 <= sbs_message.longitude <= 180


def is_valid_altitude( sbs_message ):
    # Prüft, ob die Höhe gültig ist.
    
    return sbs_message.altitude is not None and sbs_message.altitude >= 0


# Laden der JSON-Dateien
allready_detected_aircraft = []
data_structure = load_aircraft_json(JSON_FILE)
if 'aircraft' in data_structure:
    allready_detected_aircraft = data_structure['aircraft']  # zugriff auf das aircraft Array aus der JSON-Datei
else:
    print("'aircraft' key not found in the JSON data.")
    
alltime_aircraft = []
alltime_data_structure = load_aircraft_json(ALLTIME_JSON_FILE)
if 'aircraft' in alltime_data_structure:
    alltime_aircraft = alltime_data_structure['aircraft']  # zugriff auf das aircraft Array aus der JSON-Datei
else:
    print("'aircraft' key not found in the JSON data.")


# Hauptschleife
buffer = ""
while True:
    try:
        socketResponse = sock.recv(8192).decode('utf-8')
        
        if not socketResponse:
            main_logger.error("Socket antwortet nicht.")
            continue

        buffer += socketResponse
        lines = buffer.splitlines()

        
        debug_logger.debug(f"{len(lines)} Lines")

        for line in lines[:-1]:
            

            lines_logger.debug(f"Empfangene Zeile: {line}")

            current_time = time.time()

            sbs_message = parse_sbs_message(line)
            
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
                    distance = distance,
                    lat = sbs_message.latitude,
                    lon = sbs_message.longitude,
                    seen = 1,
                    last_seen = sbs_message.timestamp
                )

                # logge das aircraft
                # main_logger.info(f"Detected aircraft: {aircraft}")

                relevant_entries = [a for a in allready_detected_aircraft if a['hex'] == aircraft.hex]
                
                if relevant_entries:

                    # Prüfe, ob alle Einträge älter als NEW_ENTRY_TTL_SECONDS sind
                    all_older_than_new_entry_ttl_seconds_minutes = all(
                        current_time - entry['last_seen'] >= NEW_ENTRY_TTL_SECONDS for entry in relevant_entries
                    )

                    if all_older_than_new_entry_ttl_seconds_minutes:                                   
                        usedAction = "existing but older than 5 Min -> new aircraft"
                        add_aircraft( allready_detected_aircraft, aircraft, current_time )
                    else:

                        # Aktualisiere den jüngsten Eintrag bei sinkender Höhe
                        latest_entry = max( relevant_entries, key = lambda x: x['last_seen'] )
                        
                        #if aircraft.altitude and aircraft.altitude <= latest_entry['altitude']:
                        usedAction = "update aircraft"
                        update_aircraft(latest_entry, aircraft, current_time)
                        # else:
                            # main_logger.info(f"Höhe nicht gesunken, keine Aktualisierung für ICAO/HEX {aircraft.hex}")

                else:
                    usedAction = "new aircraft"
                    add_aircraft( allready_detected_aircraft, aircraft, current_time )


                # little debugging
                if usedAction != "nothing":
                    main_logger.info(f"********************************************************************************")
                    main_logger.info(f"Action: {usedAction}")
                    main_logger.info(f"Aircraft: {aircraft}")

                # print(usedAction)
                # print(relevant_entries)
                # print(allready_detected_aircraft)
                
                # logging.info(f"Relevant entries: {relevant_entries}")
                # logging.info(f"Detected aircraft: {allready_detected_aircraft}")
            except ValueError as e:
                main_logger.error(f"Fehler beim Verarbeiten der SBSMessage {sbs_message}: {e}")
    
        buffer = lines[-1]  # Behalte unvollständige Zeilen im Puffer

        
        # veraltete Flugzeuge separieren und zum Archivieren speichern
        final_detected = []
        for aircraft in allready_detected_aircraft:
            if current_time - aircraft['last_seen'] <= TTL_SECONDS:
                final_detected.append(aircraft)
            else:
                alltime_aircraft.append(aircraft)


        # Speichern in der gewünschten JSON-Struktur
        try:
          save_aircraft_json(JSON_FILE, {"now": time.time(), "aircraft": final_detected})
          save_aircraft_json(ALLTIME_JSON_FILE, {"now": time.time(), "aircraft": alltime_aircraft})
        except IOError as e:
            main_logger.error(f"Fehler beim Speichern der JSON-Datei: {e}")
        
        
        time.sleep(5)

    except BlockingIOError:
        time.sleep(1)

    except Exception as e:
        main_logger.error(f"Unerwarteter Fehler: {e}")
