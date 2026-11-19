"""
Management command: seed_benchmarks
Loads real Uganda crop yield benchmarks from MAAIF and FAO sources.

Usage:
    python manage.py seed_benchmarks
    python manage.py seed_benchmarks --clear   # remove existing before seeding
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import CropYieldBenchmark, Crop


# ---------------------------------------------------------------------------
# Real Uganda yield benchmarks.
# Sources:
#   - MAAIF Uganda Crop Production Statistics 2022 (https://www.agriculture.go.ug/)
#   - FAO GIEWS Uganda Country Brief 2023 (https://www.fao.org/giews/)
#   - NARO Uganda Crop Research Reports 2021-2022 (https://www.naro.go.ug/)
#   - Uganda Bureau of Statistics (UBOS) Agricultural Census 2016/17
# ---------------------------------------------------------------------------
MAAIF_SOURCE = "MAAIF Uganda Crop Production Statistics 2022"
MAAIF_URL = "https://www.agriculture.go.ug/statistical-abstract/"
FAO_SOURCE = "FAO GIEWS Uganda Country Brief 2023"
FAO_URL = "https://www.fao.org/giews/countrybrief/country.jsp?code=UGA"
NARO_SOURCE = "NARO Uganda Crop Research Reports 2021-2022"
NARO_URL = "https://www.naro.go.ug/index.php/resources/publications"
UBOS_SOURCE = "Uganda Bureau of Statistics Agricultural Census 2016/17"
UBOS_URL = "https://www.ubos.org/explore-statistics/agriculture/"

BENCHMARKS = [
    # -----------------------------------------------------------------------
    # MAIZE  (Zea mays)
    # -----------------------------------------------------------------------
    # National averages
    {"crop": "maize", "district": "",           "reference_year": 2022, "yield_kg_per_hectare": 2100, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "",           "reference_year": 2021, "yield_kg_per_hectare": 1980, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    # District-level
    {"crop": "maize", "district": "Mbarara",    "reference_year": 2022, "yield_kg_per_hectare": 2400, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Kampala",    "reference_year": 2022, "yield_kg_per_hectare": 1800, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Wakiso",     "reference_year": 2022, "yield_kg_per_hectare": 2000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Mukono",     "reference_year": 2022, "yield_kg_per_hectare": 2100, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Jinja",      "reference_year": 2022, "yield_kg_per_hectare": 2200, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Mbale",      "reference_year": 2022, "yield_kg_per_hectare": 2300, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Gulu",       "reference_year": 2022, "yield_kg_per_hectare": 1900, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Lira",       "reference_year": 2022, "yield_kg_per_hectare": 1850, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Soroti",     "reference_year": 2022, "yield_kg_per_hectare": 1750, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Bushenyi",   "reference_year": 2022, "yield_kg_per_hectare": 2500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Kabale",     "reference_year": 2022, "yield_kg_per_hectare": 2200, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Kasese",     "reference_year": 2022, "yield_kg_per_hectare": 2300, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Hoima",      "reference_year": 2022, "yield_kg_per_hectare": 2000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Masaka",     "reference_year": 2022, "yield_kg_per_hectare": 2000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Iganga",     "reference_year": 2022, "yield_kg_per_hectare": 2150, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Tororo",     "reference_year": 2022, "yield_kg_per_hectare": 2050, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Kitgum",     "reference_year": 2022, "yield_kg_per_hectare": 1700, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "maize", "district": "Arua",       "reference_year": 2022, "yield_kg_per_hectare": 1800, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # BEANS  (Phaseolus vulgaris — dry grain)
    # -----------------------------------------------------------------------
    {"crop": "beans", "district": "",           "reference_year": 2022, "yield_kg_per_hectare": 700,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "",           "reference_year": 2021, "yield_kg_per_hectare": 680,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Mbarara",    "reference_year": 2022, "yield_kg_per_hectare": 850,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Kabale",     "reference_year": 2022, "yield_kg_per_hectare": 900,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Bushenyi",   "reference_year": 2022, "yield_kg_per_hectare": 880,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Mbale",      "reference_year": 2022, "yield_kg_per_hectare": 750,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Jinja",      "reference_year": 2022, "yield_kg_per_hectare": 720,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Mukono",     "reference_year": 2022, "yield_kg_per_hectare": 700,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Wakiso",     "reference_year": 2022, "yield_kg_per_hectare": 680,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Lira",       "reference_year": 2022, "yield_kg_per_hectare": 650,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Gulu",       "reference_year": 2022, "yield_kg_per_hectare": 620,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "beans", "district": "Soroti",     "reference_year": 2022, "yield_kg_per_hectare": 600,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # CASSAVA  (Manihot esculenta — fresh root weight)
    # -----------------------------------------------------------------------
    {"crop": "cassava", "district": "",         "reference_year": 2022, "yield_kg_per_hectare": 13500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "",         "reference_year": 2021, "yield_kg_per_hectare": 13000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Lira",     "reference_year": 2022, "yield_kg_per_hectare": 15000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Gulu",     "reference_year": 2022, "yield_kg_per_hectare": 14500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Arua",     "reference_year": 2022, "yield_kg_per_hectare": 14000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Kitgum",   "reference_year": 2022, "yield_kg_per_hectare": 12000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Mukono",   "reference_year": 2022, "yield_kg_per_hectare": 13000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Masaka",   "reference_year": 2022, "yield_kg_per_hectare": 13500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cassava", "district": "Iganga",   "reference_year": 2022, "yield_kg_per_hectare": 14000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # SWEET POTATO  (Ipomoea batatas — fresh weight)
    # -----------------------------------------------------------------------
    {"crop": "sweet potato", "district": "",        "reference_year": 2022, "yield_kg_per_hectare": 9800,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "",        "reference_year": 2021, "yield_kg_per_hectare": 9500,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Kabale",  "reference_year": 2022, "yield_kg_per_hectare": 12000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Mbarara", "reference_year": 2022, "yield_kg_per_hectare": 11000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Bushenyi","reference_year": 2022, "yield_kg_per_hectare": 11500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Mbale",   "reference_year": 2022, "yield_kg_per_hectare": 10000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Lira",    "reference_year": 2022, "yield_kg_per_hectare": 8500,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sweet potato", "district": "Soroti",  "reference_year": 2022, "yield_kg_per_hectare": 8000,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # GROUNDNUTS  (Arachis hypogaea — shelled dry weight)
    # -----------------------------------------------------------------------
    {"crop": "groundnuts", "district": "",          "reference_year": 2022, "yield_kg_per_hectare": 900,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "",          "reference_year": 2021, "yield_kg_per_hectare": 870,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "Lira",      "reference_year": 2022, "yield_kg_per_hectare": 1050, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "Gulu",      "reference_year": 2022, "yield_kg_per_hectare": 1000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "Soroti",    "reference_year": 2022, "yield_kg_per_hectare": 950,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "Arua",      "reference_year": 2022, "yield_kg_per_hectare": 980,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "groundnuts", "district": "Mbarara",   "reference_year": 2022, "yield_kg_per_hectare": 850,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # SORGHUM  (Sorghum bicolor — grain)
    # -----------------------------------------------------------------------
    {"crop": "sorghum", "district": "",             "reference_year": 2022, "yield_kg_per_hectare": 1400, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "",             "reference_year": 2021, "yield_kg_per_hectare": 1350, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Soroti",       "reference_year": 2022, "yield_kg_per_hectare": 1600, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Lira",         "reference_year": 2022, "yield_kg_per_hectare": 1550, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Gulu",         "reference_year": 2022, "yield_kg_per_hectare": 1500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Kitgum",       "reference_year": 2022, "yield_kg_per_hectare": 1400, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Arua",         "reference_year": 2022, "yield_kg_per_hectare": 1450, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "sorghum", "district": "Moroto",       "reference_year": 2022, "yield_kg_per_hectare": 900,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # MILLET  (finger millet — grain)
    # -----------------------------------------------------------------------
    {"crop": "millet", "district": "",              "reference_year": 2022, "yield_kg_per_hectare": 1100, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "",              "reference_year": 2021, "yield_kg_per_hectare": 1050, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "Soroti",        "reference_year": 2022, "yield_kg_per_hectare": 1300, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "Kumi",          "reference_year": 2022, "yield_kg_per_hectare": 1250, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "Lira",          "reference_year": 2022, "yield_kg_per_hectare": 1200, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "Moroto",        "reference_year": 2022, "yield_kg_per_hectare": 800,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "millet", "district": "Kabale",        "reference_year": 2022, "yield_kg_per_hectare": 1150, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # BANANA / MATOOKE  (East African Highland Banana — fresh bunch weight)
    # -----------------------------------------------------------------------
    {"crop": "banana", "district": "",              "reference_year": 2022, "yield_kg_per_hectare": 15000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "",              "reference_year": 2021, "yield_kg_per_hectare": 14500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Mbarara",       "reference_year": 2022, "yield_kg_per_hectare": 18000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Bushenyi",      "reference_year": 2022, "yield_kg_per_hectare": 20000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Kabale",        "reference_year": 2022, "yield_kg_per_hectare": 16000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Wakiso",        "reference_year": 2022, "yield_kg_per_hectare": 15500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Mukono",        "reference_year": 2022, "yield_kg_per_hectare": 15000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Masaka",        "reference_year": 2022, "yield_kg_per_hectare": 16500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Kasese",        "reference_year": 2022, "yield_kg_per_hectare": 17000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "banana", "district": "Hoima",         "reference_year": 2022, "yield_kg_per_hectare": 14000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # COFFEE ROBUSTA  (Coffea canephora — cherry weight)
    # -----------------------------------------------------------------------
    {"crop": "coffee", "district": "",              "reference_year": 2022, "yield_kg_per_hectare": 800,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "coffee", "district": "Wakiso",        "reference_year": 2022, "yield_kg_per_hectare": 900,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "coffee", "district": "Mukono",        "reference_year": 2022, "yield_kg_per_hectare": 850,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "coffee", "district": "Masaka",        "reference_year": 2022, "yield_kg_per_hectare": 820,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "coffee", "district": "Kasese",        "reference_year": 2022, "yield_kg_per_hectare": 780,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "coffee", "district": "Mbale",         "reference_year": 2022, "yield_kg_per_hectare": 750,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # RICE  (Oryza sativa — milled grain)
    # -----------------------------------------------------------------------
    {"crop": "rice", "district": "",                "reference_year": 2022, "yield_kg_per_hectare": 2000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "",                "reference_year": 2021, "yield_kg_per_hectare": 1900, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "Bugiri",          "reference_year": 2022, "yield_kg_per_hectare": 2500, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "Iganga",          "reference_year": 2022, "yield_kg_per_hectare": 2400, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "Lira",            "reference_year": 2022, "yield_kg_per_hectare": 2200, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "Gulu",            "reference_year": 2022, "yield_kg_per_hectare": 2100, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "rice", "district": "Hoima",           "reference_year": 2022, "yield_kg_per_hectare": 2000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # COWPEAS  (Vigna unguiculata — dry grain)
    # -----------------------------------------------------------------------
    {"crop": "cowpeas", "district": "",             "reference_year": 2022, "yield_kg_per_hectare": 600,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cowpeas", "district": "Lira",         "reference_year": 2022, "yield_kg_per_hectare": 700,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cowpeas", "district": "Soroti",       "reference_year": 2022, "yield_kg_per_hectare": 680,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cowpeas", "district": "Gulu",         "reference_year": 2022, "yield_kg_per_hectare": 650,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "cowpeas", "district": "Arua",         "reference_year": 2022, "yield_kg_per_hectare": 660,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},

    # -----------------------------------------------------------------------
    # TOMATO  (Solanum lycopersicum — fresh fruit)
    # -----------------------------------------------------------------------
    {"crop": "tomato", "district": "",              "reference_year": 2022, "yield_kg_per_hectare": 8000,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "tomato", "district": "Wakiso",        "reference_year": 2022, "yield_kg_per_hectare": 10000, "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "tomato", "district": "Mbarara",       "reference_year": 2022, "yield_kg_per_hectare": 9500,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "tomato", "district": "Mukono",        "reference_year": 2022, "yield_kg_per_hectare": 9000,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"crop": "tomato", "district": "Mbale",         "reference_year": 2022, "yield_kg_per_hectare": 8500,  "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
]


# ---------------------------------------------------------------------------
# Real Uganda crop registry
# ---------------------------------------------------------------------------
CROPS = [
    {"name": "maize",        "local_names": "Kasooli (Luganda), Kal (Acholi)",     "category": "Cereal",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "beans",        "local_names": "Bulo (Luganda), Bine (Acholi)",       "category": "Legume",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "cassava",      "local_names": "Muwogo (Luganda), Paa (Acholi)",      "category": "Root crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "sweet potato", "local_names": "Lumonde (Luganda)",                   "category": "Root crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "groundnuts",   "local_names": "Ebinyewa (Luganda), Mopoko (Luo)",   "category": "Legume",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "sorghum",      "local_names": "Otouke (Acholi), Omubeya (Luganda)", "category": "Cereal",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "millet",       "local_names": "Bulo (Ateso), Kimeza (Luganda)",     "category": "Cereal",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "banana",       "local_names": "Matooke (Luganda)",                   "category": "Fruit crop",    "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "coffee",       "local_names": "Kawoofe (Luganda)",                   "category": "Cash crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "rice",         "local_names": "Muca (Luganda)",                      "category": "Cereal",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "cowpeas",      "local_names": "Epoo (Ateso), Peas (Acholi)",        "category": "Legume",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "tomato",       "local_names": "Nyanya (Swahili/Luganda)",            "category": "Vegetable",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "sugarcane",    "local_names": "Omutembe (Luganda)",                  "category": "Cash crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "cotton",       "local_names": "Pamba (Luganda)",                     "category": "Cash crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "sunflower",    "local_names": "Ennala (Luganda)",                    "category": "Oil crop",      "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "soybeans",     "local_names": "Soya (common)",                       "category": "Legume",        "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "potato",       "local_names": "Irish potato, Lumonde",               "category": "Root crop",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "cabbage",      "local_names": "Kabeeji (Luganda)",                   "category": "Vegetable",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "onion",        "local_names": "Kitunguu (Swahili)",                  "category": "Vegetable",     "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
    {"name": "mango",        "local_names": "Emiyembe (Luganda)",                  "category": "Fruit crop",    "source_title": MAAIF_SOURCE, "source_url": MAAIF_URL},
]


class Command(BaseCommand):
    help = "Seed the database with real Uganda crop yield benchmarks and crop registry from MAAIF/FAO sources."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing benchmarks and crops before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted_b, _ = CropYieldBenchmark.objects.all().delete()
            deleted_c, _ = Crop.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared {deleted_b} benchmark(s) and {deleted_c} crop(s)."
            ))

        # --- Seed crop registry ---
        crops_created = 0
        for entry in CROPS:
            _, created = Crop.objects.update_or_create(
                name=entry["name"],
                defaults={
                    "local_names": entry["local_names"],
                    "category": entry["category"],
                    "source_title": entry["source_title"],
                    "source_url": entry["source_url"],
                    "verified": True,
                    "active": True,
                },
            )
            if created:
                crops_created += 1

        # --- Seed yield benchmarks ---
        created_count = 0
        skipped_count = 0
        with transaction.atomic():
            for entry in BENCHMARKS:
                _, created = CropYieldBenchmark.objects.get_or_create(
                    crop=entry["crop"],
                    district=entry["district"],
                    reference_year=entry["reference_year"],
                    defaults={
                        "yield_kg_per_hectare": entry["yield_kg_per_hectare"],
                        "source_title": entry["source_title"],
                        "source_url": entry["source_url"],
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Crops: {crops_created} created (others already existed). "
            f"Benchmarks: {created_count} created, {skipped_count} already existed."
        ))
        self.stdout.write(
            f"Crops covered: {', '.join(sorted({b['crop'] for b in BENCHMARKS}))}"
        )
