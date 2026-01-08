import signal
import sys
import time
import json

from logic.sbs_client import SBSClient
from logic.sbs_parser import SBSParser
from logic.aircraft_tracker import AircraftTracker
from logic.aircraft import Aircraft
from logic.log_manager import LogManager
from logic.constants import Environment

from config import Config


# Konfiguration laden
config = Config(Environment.PRODUCTION)

# LogManager initialisieren
log = LogManager(config)
main_logger = log.get_logger("main")
debug_logger = log.get_logger("debug")
lines_logger = log.get_logger("lines")

# laden der aircraft registration database json file and save it in a dictionary
with open("data/database/aircraft_registrations.json", 'r', encoding='utf-8') as file:
    aircraftRegistrationDB = json.load(file)

# AircraftTracker initialisierung
aircraftTracker = AircraftTracker(config=config, log=log, aircraftRegistrationDB=aircraftRegistrationDB)

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


# Hauptschleife
buffer = ""
while True:
    try:
        lines = sbsClient.read_lines()
        debug_logger.debug(f"{len(lines)} Lines")

        if not lines:
            time.sleep(1)
            continue


        current_time = time.time()

        for line in lines:
            lines_logger.debug(f"Empfangene Zeile: {line}")

            current_time = time.time()

            sbs_message = sbsParser.parse_line(line)

            if not sbs_message:
                continue  # Überspringe ungültige Nachrichten


            debug_logger.debug(f"Nachricht: {sbs_message}")

            try:
                usedAction = "nothing"

                # Aircraft-Objekt mit minimalen Daten erstellen und Daten validiert.
                aircraft = Aircraft(
                    altitude = sbs_message.altitude,
                    lat = sbs_message.latitude,
                    lon = sbs_message.longitude,
                    aircraftRegistrationDB = aircraftRegistrationDB,
                    log = log,
                )

                if not aircraft.is_valid():
                    main_logger.warning(f"Ungültige Daten für Flugzeug {sbs_message.icao}: {aircraft}")
                    continue


                # Aircraft valid, also kompletiere die Daten
                aircraft.enrich_with_sbs_message(sbs_message, config)

                # Überprüfen, ob das Flugzeug innerhalb des definierten Radius ist
                if aircraft.distance is None or aircraft.distance >= config.RADIUS_KM:
                    continue

                # Überprüfen, ob das Flugzeug innerhalb der Höhenbeschränkungen ist
                if aircraft.altitude is None or aircraft.altitude < config.MIN_HEIGHT or aircraft.altitude > config.MAX_HEIGHT:
                    continue

                relevant_entries = aircraftTracker.get_existing_entries(aircraft.hex)

                if not relevant_entries or aircraftTracker.should_add_new(relevant_entries, current_time):
                    usedAction = "new aircraft"
                    aircraftTracker.add_aircraft( aircraft )
                elif relevant_entries and not aircraftTracker.should_add_new(relevant_entries, current_time):

                    # Aktualisiere den jüngsten Eintrag
                    latest_entry = max( relevant_entries, key = lambda x: x.last_seen )

                    # update the aircraft class only if the current distance is not none and lower than the stored distance
                    if latest_entry.distance is None or aircraft.distance < latest_entry.distance:
                        usedAction = "update aircraft"
                        aircraftTracker.update_aircraft(latest_entry, aircraft)

                #else:
                    # so nothing to do, aircraft is already in the list


                # little debugging
                if usedAction != "nothing":
                    # logge das aircraft
                    main_logger.info(f"Detected aircraft: {aircraft.hex}")
                    main_logger.info(f"********************************************************************************")
                    main_logger.info(f"Action: {usedAction}")
                    main_logger.info(f"Aircraft: hex={aircraft.hex}, registration={aircraft.registration}, altitude={aircraft.altitude}, distance={aircraft.distance}, lat={aircraft.lat}, lon={aircraft.lon}, seen={aircraft.seen}, last_seen={aircraft.last_seen}")

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
