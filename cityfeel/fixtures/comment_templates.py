"""
Szablony komentarzy w języku polskim dla fixtures CityFeel.
Komentarze są podzielone na kategorie odpowiadające emotional_value (1-5).
"""

# Komentarze dla emotional_value = 5 (bardzo pozytywne)
COMMENTS_VERY_POSITIVE = [
    "Fantastyczne miejsce! Koniecznie trzeba odwiedzić!",
    "Absolutnie przepiękne! Wrócę tu na pewno.",
    "Wspaniałe doświadczenie, polecam każdemu!",
    "Najpiękniejsze miejsce w Trójmieście!",
    "Magiczne! Zachwycona atmosferą.",
    "Idealne na romantyczny spacer.",
    "Cudowny widok, niesamowita energia!",
    "Świetne miejsce, super klimat!",
    "Rewelacja! Najlepsze miejsce ever.",
    "Przepięknie tutaj, polecam w 100%!",
]

# Komentarze dla emotional_value = 4 (pozytywne)
COMMENTS_POSITIVE = [
    "Bardzo fajnie, polecam!",
    "Miła atmosfera, warto odwiedzić.",
    "Przyjemne miejsce, spędziłem tu świetny czas.",
    "Ładne miejsce, polecam na spacer.",
    "Bardzo mi się podobało!",
    "Fajne miejsce, wrócę tu jeszcze.",
    "Spoko miejsce, dobra atmosfera.",
    "Czysto, zadbane, polecam.",
    "Świetnie spędzony czas!",
    "Polecam, naprawdę warto!",
]

# Komentarze dla emotional_value = 3 (neutralne)
COMMENTS_NEUTRAL = [
    "W porządku, nic specjalnego.",
    "Całkiem niezłe miejsce.",
    "Standard, jak wszędzie.",
    "Można przyjść, ale nie jest to must-see.",
    "Przeciętnie, spodziewałem się więcej.",
    "Okej, ale są lepsze miejsca.",
    "Średnio, nic szczególnego.",
    "W miarę ok, nic wybitnego.",
    "Takie sobie.",
    "Normalnie, bez szału.",
]

# Komentarze dla emotional_value = 2 (negatywne)
COMMENTS_NEGATIVE = [
    "Nie polecam, mogło być lepiej.",
    "Rozczarowanie, spodziewałem się więcej.",
    "Nie wrócę tu ponownie.",
    "Słabe miejsce, nie warto.",
    "Przeciętnie, nic ciekawego.",
    "Niezbyt, są lepsze miejsca.",
    "Nie jestem zadowolony.",
    "Słabo, nie polecam.",
    "Średnio utrzymane.",
    "Mogło być zdecydowanie lepiej.",
]

# Komentarze dla emotional_value = 1 (bardzo negatywne)
COMMENTS_VERY_NEGATIVE = [
    "Okropne miejsce, nie polecam!",
    "Fatalnie! Nigdy więcej!",
    "Strata czasu i pieniędzy.",
    "Tragedia, bardzo źle.",
    "Koszmarne doświadczenie.",
    "Brudno, zaniedbane, okropne.",
    "Tłoczno, hałaśliwie, nieznośnie.",
    "Bardzo słabo, nie polecam nikomu!",
    "Koszmar! Straszne miejsce.",
    "Najgorsze miejsce jakie odwiedziłem.",
]

# Komentarze odpowiedzi (do EmotionPoint) - uniwersalne
COMMENTS_REPLY = [
    "Dokładnie tak myślę!",
    "Zgadzam się w 100%!",
    "Mam podobne odczucia.",
    "To prawda, tak było.",
    "Podzielam twoją opinię.",
    "Całkowicie się zgadzam!",
    "Ja też tak uważam.",
    "Dokładnie! Tak jest!",
    "Mam identyczne wrażenia.",
    "Świetnie ujęte, zgadzam się!",
    "Nie zgadzam się, moje doświadczenie było inne.",
    "Ciekawe, ja miałem zupełnie inne wrażenia.",
    "Różnie bywa, ja byłem bardziej zadowolony.",
]

# Mapowanie emotional_value na szablony komentarzy
COMMENT_TEMPLATES_BY_VALUE = {
    1: COMMENTS_VERY_NEGATIVE,
    2: COMMENTS_NEGATIVE,
    3: COMMENTS_NEUTRAL,
    4: COMMENTS_POSITIVE,
    5: COMMENTS_VERY_POSITIVE,
}
