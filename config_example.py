from logic.constants import Environment
class Config:
    def __init__(self, environment: Environment):
        
        if not isinstance(environment, Environment):
            raise TypeError("Environment must be an instance of Environment Enum")

        self.ENV = environment
        self.HOST = 'localhost'
        self.PORT = 30003
        self.HOME_LAT = 51.133333
        self.HOME_LON = 10.416667
        self.RADIUS_KM = 4
        self.MIN_HEIGHT = 0
        self.MAX_HEIGHT = 10000
        self.TTL_HOURS = 24
        self.TTL_SECONDS = self.TTL_HOURS * 3600
        self.NEW_ENTRY_TTL_SECONDS = 3600

        if environment == self.ENV.DEVELOPMENT:
            self.HOST = '192.168.1.42'
            self.DUMP1090DATAFOLDER = "./data"
            self.LOG_DIRECTORY = "./log"
        else:
            self.DUMP1090DATAFOLDER = "/run/dump1090-mutability"
            self.LOG_DIRECTORY = "/var/log/aircraftoverhome/"

        self.JSON_FILE = f"{self.DUMP1090DATAFOLDER}/aircraft_over_home.json"
        self.ALLTIME_JSON_FILE = f"{self.DUMP1090DATAFOLDER}/aircraft_over_home_alltime.json"
