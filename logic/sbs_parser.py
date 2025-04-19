# sbs_parser.py

import time
from collections import namedtuple
from utils import safe_int, safe_float

SBSMessage = namedtuple('SBSMessage', [
    'message_type',
    'transmission_type',
    'icao',
    'altitude',
    'latitude',
    'longitude',
    'timestamp'
])

class SBSParser:
    def parse_line(self, line: str):
        fields = line.split(',')

        try:
            if len(fields) < 10:
                raise ValueError("Unvollständige SBS-Nachricht(<10).")

            message_type = fields[0]
            transmission_type = safe_int(fields[1])

            if message_type != 'MSG' or transmission_type != 3:
                return None

            if len(fields) < 22:
                raise ValueError("Unvollständige MSG-Nachricht(<22).")

            icao = fields[4]
            altitude = safe_int(fields[11])
            latitude = safe_float(fields[14])
            longitude = safe_float(fields[15])

            if not icao:
                raise ValueError("Fehlende ICAO-Adresse.")

            return SBSMessage(
                message_type=message_type,
                transmission_type=transmission_type,
                icao=icao,
                altitude=altitude,
                latitude=latitude,
                longitude=longitude,
                timestamp=time.time()
            )

        except (IndexError, ValueError) as e:
            # Logging optional hier, oder raise für Tests
            return None