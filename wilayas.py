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
    "Béjaïa",
    "Biskra",
    "Béchar",
    "Blida",
    "Bouira",
    "Tamanrasset",
    "Tébessa",
    "Tlemcen",
    "Tiaret",
    "Tizi Ouzou",
    "Alger",
    "Djelfa",
    "Jijel",
    "Sétif",
    "Saïda",
    "Skikda",
    "Sidi Bel Abbès",
    "Annaba",
    "Guelma",
    "Constantine",
    "Médéa",
    "Mostaganem",
    "M'Sila",
    "Mascara",
    "Ouargla",
    "Oran",
    "El Bayadh",
    "Illizi",
    "Bordj Bou Arreridj",
    "Boumerdès",
    "El Tarf",
    "Tindouf",
    "Tissemsilt",
    "El Oued",
    "Khenchela",
    "Souk Ahras",
    "Tipaza",
    "Mila",
    "Aïn Defla",
    "Naâma",
    "Aïn Témouchent",
    "Ghardaïa",
    "Relizane",
    "Timimoun",
    "Bordj Badji Mokhtar",
    "Ouled Djellal",
    "Béni Abbès",
    "In Salah",
    "In Guezzam",
    "Touggourt",
    "Djanet",
    "El M'Ghair",
    "El Meniaa",
]

# Normalized mapping for case-insensitive matching
ALGERIAN_WILAYAS_NORMALIZED = {w.lower(): w for w in ALGERIAN_WILAYAS}

# Also include common variations
ALGERIAN_WILAYAS_NORMALIZED.update({
    "algiers": "Alger",
    "oran": "Oran",
    "constantine": "Constantine",
    "annaba": "Annaba",
    "setif": "Sétif",
    "tlemcen": "Tlemcen",
    "bejaia": "Béjaïa",
    "jijel": "Jijel",
    "skikda": "Skikda",
    "blida": "Blida",
    "tizi ouzou": "Tizi Ouzou",
    "boumerdes": "Boumerdès",
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
