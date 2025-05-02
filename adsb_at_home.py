import signal
import sys
import time
import json

from logic.sbs_client import SBSClient
from logic.sbs_parser import SBSParser
from logic.aircraft_tracker import AircraftTracker
from logic.aircraft import Aircraft
from logic.log_manager import LogManager
from config import Config

# Konfiguration laden
config = Config("DEVELOPMENT")

# LogManager initialisieren
log = LogManager(config)
main_logger = log.get_logger("main")
debug_logger = log.get_logger("debug")
lines_logger = log.get_logger("lines")

# AircraftTracker initialisierung
aircraftTracker = AircraftTracker(config)

# SBSClient initialisierung
sbsClient = SBSClient(config, logger=main_logger)
sbsClient.connect()

# SBSParser initialisierung
sbsParser = SBSParser()

# STRG+C-Handler
def signal_handler(sig, frame):
    main_logger.info("Skript wird beendet.")
    sbsClient.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


main_logger.info(f"Skript gestartet: {config.HOST}:{config.PORT}")

# laden der aircraft registration database json file and save it in a dictionary
with open(config.DUMP1090DATAFOLDER + "/database/aircraft_registrations.json", 'r') as file:
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
        lines = sbsClient.read_lines()

        debug_logger.debug(f"{len(lines)} Lines")

        if not lines:
            time.sleep(1)
            continue
        

        for line in lines:

            lines_logger.debug(f"Empfangene Zeile: {line}")

            current_time = time.time()

            sbs_message = sbsParser.parse_line(line)
            
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


                usedAction = "nothing"

                aircraft = Aircraft(
                    hex = sbs_message.icao,
                    altitude = sbs_message.altitude,
                    lat = sbs_message.latitude,
                    lon = sbs_message.longitude,
                    timestamp = sbs_message.timestamp,                    
                    config = config
                )

                # Überprüfen, ob das Flugzeug innerhalb des definierten Radius ist
                if aircraft.distance is None or aircraft.distance >= config.RADIUS_KM:
                    continue


                # add aircrfaft registration to the aircraft object    
                registration = aircraftRegistrationDB.get(aircraft.hex.upper())  # `.get()` gibt None zurück, falls der Key nicht existiert
                aircraft.set_registration(registration)

                if registration:
                    main_logger.info(f"Registration for {sbs_message.icao}: {registration}")
                else:
                    main_logger.warning(f"Key {sbs_message.icao} not found in JSON data.")
              
                relevant_entries = aircraftTracker.get_existing_entries(aircraft.hex)
                
                if not relevant_entries or aircraftTracker.should_add_new(relevant_entries, current_time):
                    usedAction = "new aircraft"
                    aircraftTracker.add_aircraft( aircraft )
                elif relevant_entries and not aircraftTracker.should_add_new(relevant_entries, current_time):
                      
                    # Aktualisiere den jüngsten Eintrag bei sinkender Höhe
                    latest_entry = max( relevant_entries, key = lambda x: x.last_seen )
                    
                    # aircraft nur aktualisieren, wenn entfernung niedriger ist als die gespeichert Entfernung
                    if aircraft.distance < latest_entry.distance:
                        usedAction = "update aircraft"
                        aircraftTracker.update_aircraft(latest_entry, aircraft)
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
        aircraftTracker.cleanup_old(current_time)

        # Speichern in der gewünschten JSON-Struktur
        try:
            aircraftTracker.save_all()            
        except IOError as e:
            main_logger.error(f"Fehler beim Speichern der JSON-Datei: {e}")
        
        
        time.sleep(5)

    except BlockingIOError:
        time.sleep(1)

    except Exception as e:
        main_logger.error(f"Unerwarteter Fehler: {e}")
