"""
Dane 50 lokalizacji w Trójmieście dla fixtures CityFeel.
Każda lokalizacja ma: name, lon (longitude), lat (latitude), cluster.

Cluster określa typ lokalizacji i wpływa na rozkład emotional_value:
- sopot_positive: Sopot turystyczny (emotional_value 4-5)
- gdansk_oldtown_positive: Gdańsk Stare Miasto (emotional_value 4-5)
- gdynia_bulwary_positive: Gdynia bulwary (emotional_value 4-5)
- gdansk_peripheral_negative: Gdańsk dzielnice peryferyjne (emotional_value 1-2)
- gdynia_residential_negative: Gdynia dzielnice mieszkalne (emotional_value 1-2)
- neutral: Lokalizacje mieszane (emotional_value 2-4)
"""

LOCATIONS = [
    # Sopot - Strefa Turystyczna (10 lokalizacji) - POZYTYWNE
    {"name": "Molo w Sopocie", "lon": 18.5695, "lat": 54.4438, "cluster": "sopot_positive"},
    {"name": "Krzywy Domek", "lon": 18.5672, "lat": 54.4420, "cluster": "sopot_positive"},
    {"name": "Plaża Sopocka", "lon": 18.5700, "lat": 54.4415, "cluster": "sopot_positive"},
    {"name": "Ulica Monte Cassino", "lon": 18.5665, "lat": 54.4425, "cluster": "sopot_positive"},
    {"name": "Łazienki Północne Sopot", "lon": 18.5680, "lat": 54.4445, "cluster": "sopot_positive"},
    {"name": "Kawiarnia na Żeromskiego", "lon": 18.5668, "lat": 54.4432, "cluster": "sopot_positive"},
    {"name": "Park Północny Sopot", "lon": 18.5675, "lat": 54.4450, "cluster": "sopot_positive"},
    {"name": "Opera Leśna", "lon": 18.5620, "lat": 54.4380, "cluster": "sopot_positive"},
    {"name": "Sopockie Muszle", "lon": 18.5688, "lat": 54.4412, "cluster": "sopot_positive"},
    {"name": "Restauracja Przystań Sopot", "lon": 18.5710, "lat": 54.4428, "cluster": "sopot_positive"},

    # Gdańsk - Stare Miasto (8 lokalizacji) - POZYTYWNE
    {"name": "Długi Targ", "lon": 18.6538, "lat": 54.3489, "cluster": "gdansk_oldtown_positive"},
    {"name": "Bazylika Mariacka", "lon": 18.6530, "lat": 54.3490, "cluster": "gdansk_oldtown_positive"},
    {"name": "Fontanna Neptuna", "lon": 18.6536, "lat": 54.3486, "cluster": "gdansk_oldtown_positive"},
    {"name": "Złota Brama", "lon": 18.6525, "lat": 54.3505, "cluster": "gdansk_oldtown_positive"},
    {"name": "Ulica Mariacka", "lon": 18.6545, "lat": 54.3485, "cluster": "gdansk_oldtown_positive"},
    {"name": "Gdańskie Koło Widokowe", "lon": 18.6555, "lat": 54.3492, "cluster": "gdansk_oldtown_positive"},
    {"name": "Muzeum Bursztynu", "lon": 18.6520, "lat": 54.3510, "cluster": "gdansk_oldtown_positive"},
    {"name": "Kawiarnia Drukarnia", "lon": 18.6528, "lat": 54.3495, "cluster": "gdansk_oldtown_positive"},

    # Gdynia - Bulwary i Marina (7 lokalizacji) - POZYTYWNE
    {"name": "Molo w Gdyni", "lon": 18.5515, "lat": 54.5195, "cluster": "gdynia_bulwary_positive"},
    {"name": "Bulwary Gdyńskie", "lon": 18.5505, "lat": 54.5180, "cluster": "gdynia_bulwary_positive"},
    {"name": "Akwarium Gdyńskie", "lon": 18.5520, "lat": 54.5188, "cluster": "gdynia_bulwary_positive"},
    {"name": "Plaża Miejska Gdynia", "lon": 18.5495, "lat": 54.5170, "cluster": "gdynia_bulwary_positive"},
    {"name": "Skwer Kościuszki", "lon": 18.5540, "lat": 54.5190, "cluster": "gdynia_bulwary_positive"},
    {"name": "Marina Gdynia", "lon": 18.5525, "lat": 54.5205, "cluster": "gdynia_bulwary_positive"},
    {"name": "Kamienica Żeromskiego", "lon": 18.5535, "lat": 54.5175, "cluster": "gdynia_bulwary_positive"},

    # Gdańsk - Dzielnice Peryferyjne (8 lokalizacji) - NEGATYWNE
    {"name": "Parking Zaspa", "lon": 18.6125, "lat": 54.3755, "cluster": "gdansk_peripheral_negative"},
    {"name": "Przystanek PKM Zaspa", "lon": 18.6145, "lat": 54.3765, "cluster": "gdansk_peripheral_negative"},
    {"name": "Sklep Biedronka Zaspa", "lon": 18.6130, "lat": 54.3750, "cluster": "gdansk_peripheral_negative"},
    {"name": "Osiedle Chełm", "lon": 18.5980, "lat": 54.3950, "cluster": "gdansk_peripheral_negative"},
    {"name": "Parking Przymorze", "lon": 18.6025, "lat": 54.4050, "cluster": "gdansk_peripheral_negative"},
    {"name": "Dworzec PKS Wrzeszcz", "lon": 18.6085, "lat": 54.3820, "cluster": "gdansk_peripheral_negative"},
    {"name": "Galeria Metropolia", "lon": 18.6010, "lat": 54.4020, "cluster": "gdansk_peripheral_negative"},
    {"name": "Rondo Sobótki", "lon": 18.6095, "lat": 54.3740, "cluster": "gdansk_peripheral_negative"},

    # Gdynia - Dzielnice Mieszkalne (5 lokalizacji) - NEGATYWNE
    {"name": "Dworzec PKP Gdynia Główna", "lon": 18.5385, "lat": 54.5210, "cluster": "gdynia_residential_negative"},
    {"name": "Parking Chwarzno", "lon": 18.5245, "lat": 54.5025, "cluster": "gdynia_residential_negative"},
    {"name": "Osiedle Witomino", "lon": 18.5185, "lat": 54.5425, "cluster": "gdynia_residential_negative"},
    {"name": "Centrum Handlowe Klif", "lon": 18.5325, "lat": 54.5295, "cluster": "gdynia_residential_negative"},
    {"name": "Sklep Żabka Chylonia", "lon": 18.5105, "lat": 54.4950, "cluster": "gdynia_residential_negative"},

    # Gdańsk - Parki i Inne (7 lokalizacji) - MIESZANE
    {"name": "Park Oliwski", "lon": 18.5710, "lat": 54.4075, "cluster": "neutral"},
    {"name": "Westerplatte", "lon": 18.6720, "lat": 54.4065, "cluster": "neutral"},
    {"name": "Ogród Botaniczny UG", "lon": 18.5795, "lat": 54.3955, "cluster": "neutral"},
    {"name": "Parking Oliwa", "lon": 18.5725, "lat": 54.4085, "cluster": "neutral"},
    {"name": "Plaża Stogi", "lon": 18.6820, "lat": 54.3615, "cluster": "neutral"},
    {"name": "PKS Gdańsk Oliwa", "lon": 18.5705, "lat": 54.4090, "cluster": "neutral"},
    {"name": "Jarmark Dominikański", "lon": 18.6585, "lat": 54.3515, "cluster": "neutral"},

    # Sopot - Poza Centrum (5 lokalizacji) - MIESZANE
    {"name": "Aquapark Sopot", "lon": 18.5455, "lat": 54.4295, "cluster": "neutral"},
    {"name": "Park Brodwino", "lon": 18.5555, "lat": 54.4525, "cluster": "neutral"},
    {"name": "SKM Sopot Kamienny Potok", "lon": 18.5525, "lat": 54.4365, "cluster": "neutral"},
    {"name": "Ergo Arena", "lon": 18.5815, "lat": 54.4145, "cluster": "neutral"},
    {"name": "Lidl Sopot Karlikowo", "lon": 18.5485, "lat": 54.4335, "cluster": "neutral"},
]

# Mapowanie clusterów na emotional_value ranges
CLUSTER_EMOTIONS = {
    "sopot_positive": [4, 5],
    "gdansk_oldtown_positive": [4, 5],
    "gdynia_bulwary_positive": [4, 5],
    "gdansk_peripheral_negative": [1, 2],
    "gdynia_residential_negative": [1, 2],
    "neutral": [2, 3, 4],
}

# Weryfikacja ilości lokalizacji
assert len(LOCATIONS) == 50, f"Expected 50 locations, got {len(LOCATIONS)}"

# Weryfikacja unikalności nazw
names = [loc["name"] for loc in LOCATIONS]
assert len(names) == len(set(names)), "Location names must be unique!"
