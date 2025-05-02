# logic/aircraft_tracker.py

import time
import json
from logic.aircraft import Aircraft  # neue Aircraft-Klasse importieren

class AircraftTracker:
    def __init__(self, config, log, aircraftRegistrationDB):
        self.config = config
        self.log = log
        self.aircraft_db = aircraftRegistrationDB

        self.current_aircraft = [
            Aircraft.from_dict(a, config=self.config, log=self.log, aircraftRegistrationDB=self.aircraft_db)
            for a in self._load(self.config.JSON_FILE)
        ]

        self.alltime_aircraft = [
            Aircraft.from_dict(a, config=self.config, log=self.log, aircraftRegistrationDB=self.aircraft_db)
            for a in self._load(self.config.ALLTIME_JSON_FILE)
        ]

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f).get("aircraft", [])
        except:
            return []

    def _save(self, path, aircraft_list):
        with open(path, 'w') as f:
            # Aircraft-Objekte → Dictionaries
            json.dump({"now": time.time(), "aircraft": [a.to_dict() for a in aircraft_list]}, f, indent=4)

    def add_aircraft(self, aircraft: Aircraft):
        self.current_aircraft.append(aircraft)

    def update_aircraft(self, existing_aircraft: Aircraft, new_aircraft: Aircraft):
        # gezielt Werte aktualisieren
        existing_aircraft.altitude = new_aircraft.altitude
        existing_aircraft.distance = new_aircraft.distance
        existing_aircraft.lat = new_aircraft.lat
        existing_aircraft.lon = new_aircraft.lon
        existing_aircraft.last_seen = new_aircraft.last_seen
        existing_aircraft.seen += 1  # könnte man so zählen

    def get_existing_entries(self, hex_code):
        return [a for a in self.current_aircraft if a.hex == hex_code]

    def should_add_new(self, entries, current_time):
        return all(current_time - e.last_seen >= self.config.NEW_ENTRY_TTL_SECONDS for e in entries)

    def cleanup_old(self, current_time):
        still_valid = []
        for aircraft in self.current_aircraft:
            if current_time - aircraft.last_seen <= self.config.TTL_SECONDS:
                still_valid.append(aircraft)
            else:
                self.alltime_aircraft.append(aircraft)
        self.current_aircraft = still_valid

    def save_all(self):
        self._save(self.config.JSON_FILE, self.current_aircraft)
        self._save(self.config.ALLTIME_JSON_FILE, self.alltime_aircraft)
