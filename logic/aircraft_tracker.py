import time
import json
from collections import namedtuple

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

class AircraftTracker:
    def __init__(self, json_path_current, json_path_alltime, ttl_seconds, new_entry_ttl):
        self.json_path_current = json_path_current
        self.json_path_alltime = json_path_alltime
        self.ttl_seconds = ttl_seconds
        self.new_entry_ttl = new_entry_ttl

        self.current_aircraft = self._load(self.json_path_current)
        self.alltime_aircraft = self._load(self.json_path_alltime)

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f).get("aircraft", [])
        except:
            return []

    def _save(self, path, aircraft_list):
        with open(path, 'w') as f:
            json.dump({"now": time.time(), "aircraft": aircraft_list}, f, indent=4)

    def add_aircraft(self, aircraft: Aircraft):
        self.current_aircraft.append(aircraft._asdict())

    def update_aircraft(self, entry: dict, new_aircraft: Aircraft):
        entry.update({
            "altitude": new_aircraft.altitude,
            "distance": new_aircraft.distance,
            "lat": new_aircraft.lat,
            "lon": new_aircraft.lon,
            "seen": 1,
            "last_seen": new_aircraft.last_seen
        })

    def get_existing_entries(self, hex_code):
        return [a for a in self.current_aircraft if a["hex"] == hex_code]

    def should_add_new(self, entries, current_time):
        return all(current_time - e["last_seen"] >= self.new_entry_ttl for e in entries)

    def cleanup_old(self, current_time):
        final = []
        for aircraft in self.current_aircraft:
            if current_time - aircraft['last_seen'] <= self.ttl_seconds:
                final.append(aircraft)
            else:
                self.alltime_aircraft.append(aircraft)
        self.current_aircraft = final

    def save_all(self):
        self._save(self.json_path_current, self.current_aircraft)
        self._save(self.json_path_alltime, self.alltime_aircraft)
