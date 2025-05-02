# constants.py

from enum import Enum

class Environment(Enum):
    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    
# example: further Enums:
# class AircraftType(Enum):
#     CIVIL = "civil"
#     MILITARY = "military"
#     DRONE = "drone"