"""
List of all 58 official Algerian Wilayas.
Used for validation as per PRD requirements.
"""
ALGERIAN_WILAYAS = [
    "Adrar",
    "Chlef",
    "Laghouat",
    "Oum El Bouaghi",
    "Batna",
    "BÃ©jaÃ¯a",
    "Biskra",
    "BÃ©char",
    "Blida",
    "Bouira",
    "Tamanrasset",
    "TÃ©bessa",
    "Tlemcen",
    "Tiaret",
    "Tizi Ouzou",
    "Alger",
    "Djelfa",
    "Jijel",
    "SÃ©tif",
    "SaÃ¯da",
    "Skikda",
    "Sidi Bel AbbÃ¨s",
    "Annaba",
    "Guelma",
    "Constantine",
    "MÃ©dÃ©a",
    "Mostaganem",
    "M'Sila",
    "Mascara",
    "Ouargla",
    "Oran",
    "El Bayadh",
    "Illizi",
    "Bordj Bou Arreridj",
    "BoumerdÃ¨s",
    "El Tarf",
    "Tindouf",
    "Tissemsilt",
    "El Oued",
    "Khenchela",
    "Souk Ahras",
    "Tipaza",
    "Mila",
    "AÃ¯n Defla",
    "NaÃ¢ma",
    "AÃ¯n TÃ©mouchent",
    "GhardaÃ¯a",
    "Relizane",
    "Timimoun",
    "Bordj Badji Mokhtar",
    "Ouled Djellal",
    "BÃ©ni AbbÃ¨s",
    "In Salah",
    "In Guezzam",
    "Touggourt",
    "Djanet",
    "El M'Ghair",
    "El Meniaa",
]

# Normalized mapping for case-insensitive matching
ALGERIAN_WILAYAS_NORMALIZED = {w.lower(): w for w in ALGERIAN_WILAYAS}


ALGERIAN_WILAYAS_NORMALIZED.update({
    "algiers": "Alger",
    "oran": "Oran",
    "constantine": "Constantine",
    "annaba": "Annaba",
    "setif": "SÃ©tif",
    "tlemcen": "Tlemcen",
    "bejaia": "BÃ©jaÃ¯a",
    "jijel": "Jijel",
    "skikda": "Skikda",
    "blida": "Blida",
    "tizi ouzou": "Tizi Ouzou",
    "boumerdes": "BoumerdÃ¨s",
})

# List for schema (exact names)
ALGERIAN_WILAYAS_LIST = ALGERIAN_WILAYAS


def is_valid_wilaya(name: str) -> bool:
    """Check if a wilaya name is valid."""
    if not name or not isinstance(name, str):
        return False
    return name.lower() in ALGERIAN_WILAYAS_NORMALIZED


def normalize_wilaya(name: str) -> str:
    """Normalize wilaya name to canonical form."""
    if not name:
        return name
    key = name.lower().strip()
    return ALGERIAN_WILAYAS_NORMALIZED.get(key, name)

# Wilaya code mapping (1-58 in official order)
WILAYA_CODE_TO_NAME = {
    1:  Adrar, 2: Chlef, 3: Laghouat, 4: Oum El Bouaghi, 5: Batna, 6: Bejaia, 7: Biskra, 8: Bechar, 9: Blida,
    10: Bouira, 11: Tamanrasset, 12: Tebessa, 13: Tlemcen, 14: Tiaret, 15: Tizi Ouzou, 16: Alger, 17: Djelfa,
    18: Jijel, 19: Setif, 20: Saida, 21: Skikda, 22: Sidi Bel Abbes, 23: Annaba, 24: Guelma, 25: Constantine,
    26: Medea, 27: Mostaganem, 28: MSila, 29: Mascara, 30: Ouargla, 31: Oran, 32: El Bayadh, 33: Illizi,
 34: Bordj Bou Arreridj, 35: Boumerdes, 36: El Tarf, 37: Tindouf, 38: Tissemsilt, 39: El Oued, 40: Khenchela,
 41: Souk Ahras, 42: Tipaza, 43: Mila, 44: Ain Defla, 45: Naama, 46: Ain Temouchent, 47: Ghardaia, 48: Relizane,
 49: Timimoun, 50: Bordj Badji Mokhtar, 51: Ouled Djellal, 52: Beni Abbes, 53: In Salah, 54: In Guezzam,
 55: Touggourt, 56: Djanet, 57: El MGhair, 58: El Meniaa,
}
def get_wilaya_name(code):
    if isinstance(code, str):
        try: code = int(code)
        except Exception: return 
 return WILAYA_CODE_TO_NAME.get(code, )
def get_wilaya_code(name):
    if not name: return 0
    try: norm = normalize_wilaya(name)
    except Exception: norm = str(name).lower().strip()
    for c,n in WILAYA_CODE_TO_NAME.items():
        if n.lower() == norm.lower(): return c
    return 0

# Wilaya code mapping (1-58 in official order)
WILAYA_CODE_TO_NAME = {
    1:  Adrar, 2: Chlef, 3: Laghouat, 4: Oum El Bouaghi, 5: Batna, 6: Bejaia, 7: Biskra, 8: Bechar, 9: Blida,
    10: Bouira, 11: Tamanrasset, 12: Tebessa, 13: Tlemcen, 14: Tiaret, 15: Tizi Ouzou, 16: Alger, 17: Djelfa,
    18: Jijel, 19: Setif, 20: Saida, 21: Skikda, 22: Sidi Bel Abbes, 23: Annaba, 24: Guelma, 25: Constantine,
    26: Medea, 27: Mostaganem, 28: MSila, 29: Mascara, 30: Ouargla, 31: Oran, 32: El Bayadh, 33: Illizi,
 34: Bordj Bou Arreridj, 35: Boumerdes, 36: El Tarf, 37: Tindouf, 38: Tissemsilt, 39: El Oued, 40: Khenchela,
 41: Souk Ahras, 42: Tipaza, 43: Mila, 44: Ain Defla, 45: Naama, 46: Ain Temouchent, 47: Ghardaia, 48: Relizane,
 49: Timimoun, 50: Bordj Badji Mokhtar, 51: Ouled Djellal, 52: Beni Abbes, 53: In Salah, 54: In Guezzam,
 55: Touggourt, 56: Djanet, 57: El MGhair, 58: El Meniaa,
}
def get_wilaya_name(code):
    if isinstance(code, str):
        try: code = int(code)
        except Exception: return 
 return WILAYA_CODE_TO_NAME.get(code, )
def get_wilaya_code(name):
    if not name: return 0
    try: norm = normalize_wilaya(name)
    except Exception: norm = str(name).lower().strip()
    for c,n in WILAYA_CODE_TO_NAME.items():
        if n.lower() == norm.lower(): return c
    return 0

