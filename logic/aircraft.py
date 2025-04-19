import time
from utils import haversine

class Aircraft:
    def __init__(self, hex, registration=None, altitude=None, lat=None, lon=None, timestamp=None):
        self.hex = hex
        self.registration = registration
        self.altitude = altitude
        self.lat = lat
        self.lon = lon
        self.last_seen = timestamp or time.time()
        self.seen = 1
        self.distance = None  # wird dynamisch berechnet

    def is_valid_position(self):
        return self.lat is not None and self.lon is not None and -90 <= self.lat <= 90 and -180 <= self.lon <= 180

    def is_valid_altitude(self):
        return self.altitude is not None and self.altitude >= 0

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
    def from_dict(data):
        ac = Aircraft(
            hex=data.get("hex"),
            registration=data.get("registration"),
            altitude=data.get("altitude"),
            lat=data.get("lat"),
            lon=data.get("lon"),
            timestamp=data.get("last_seen")
        )
        ac.distance = data.get("distance")
        ac.seen = data.get("seen", 1)
        return ac
