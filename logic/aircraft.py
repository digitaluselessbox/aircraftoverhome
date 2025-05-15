# logic/aircraft.py

import time
from utils import haversine

class Aircraft:
    def __init__(self, hex=None, registration=None, altitude=None, lat=None, lon=None, timestamp=None, config=None, aircraftRegistrationDB=None, log=None):
        self.config = config
        self.hex = hex
        self.registration = registration
        self.altitude = altitude
        self.lat = lat
        self.lon = lon
        self.last_seen = timestamp or time.time()
        self.seen = 1
        self.distance = None
        self.aircraftRegistrationDB = aircraftRegistrationDB  # Hier wird die Datenbank übergeben
        self.log = log  # Hier wird der Logger übergeben

        # Falls Config übergeben wurde: distance sofort berechnen
        if config:
            self.calculate_distance(config.HOME_LAT, config.HOME_LON)

            # add aircraft registration to the aircraft object    
            self.set_registration()

    def enrich_with_sbs_message(self, sbs_message, config):
        self.hex = sbs_message.icao
        self.last_seen = sbs_message.timestamp
        self.calculate_distance(config.HOME_LAT, config.HOME_LON)

    def is_valid_position(self):
        return self.lat is not None and self.lon is not None and -90 <= self.lat <= 90 and -180 <= self.lon <= 180

    def is_valid_altitude(self):
        return self.altitude is not None and self.altitude >= self.config.MIN_HEIGHT and self.altitude <= self.config.MAX_HEIGHT

    def is_valid(self):
        return self.is_valid_altitude() and self.is_valid_position()

    def calculate_distance(self, home_lat, home_lon):
        if self.is_valid_position():
            self.distance = haversine(home_lat, home_lon, self.lat, self.lon)
        return self.distance

    def to_dict(self):
        return {
            "hex": self.hex,
            "registration": self.registration,
            "altitude": self.altitude,
            "distance": self.distance,
            "lat": self.lat,
            "lon": self.lon,
            "seen": self.seen,
            "last_seen": self.last_seen
        }

    @staticmethod
    def from_dict(data, config=None, log=None, aircraftRegistrationDB=None):
        main_logger = log.get_logger("main")
        main_logger.info(f"Aircraft.from_dict: {data}")
        return Aircraft(
            hex=data.get("hex"),
            registration=data.get("registration"),
            altitude=data.get("altitude"),
            lat=data.get("lat"),
            lon=data.get("lon"),
            timestamp=data.get("last_seen"),
            config=config,
            log=log,
            aircraftRegistrationDB=aircraftRegistrationDB            
        )

    def set_registration(self):
        main_logger = self.log.get_logger("main")
        main_logger.info(f"self.hex={self.hex}")
        registration = self.aircraftRegistrationDB.get(self.hex.upper())

        if registration:
            main_logger.info(f"Registration for {self.hex}: {registration}")
            self.registration = registration
        else:
            main_logger.warning(f"Key {self.hex} not found in JSON data.")
