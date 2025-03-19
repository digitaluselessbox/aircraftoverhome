import math

# utils.py
def safe_int(value):
    """Sicheres Umwandeln eines Werts in eine Ganzzahl"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_float(value):
    """Sicheres Umwandeln eines Werts in eine Gleitkommazahl"""
    try:
        return float(value.strip()) if value.strip() else None
    except (ValueError, TypeError):
        return None
    
# Distanzberechnung
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
