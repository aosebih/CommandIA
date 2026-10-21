"""Canonical Algerian wilaya names and code helpers."""

import re
import unicodedata
from typing import Optional, Union


WILAYA_CODE_TO_NAME = {
    1: "Adrar",
    2: "Chlef",
    3: "Laghouat",
    4: "Oum El Bouaghi",
    5: "Batna",
    6: "Béjaïa",
    7: "Biskra",
    8: "Béchar",
    9: "Blida",
    10: "Bouira",
    11: "Tamanrasset",
    12: "Tébessa",
    13: "Tlemcen",
    14: "Tiaret",
    15: "Tizi Ouzou",
    16: "Alger",
    17: "Djelfa",
    18: "Jijel",
    19: "Sétif",
    20: "Saïda",
    21: "Skikda",
    22: "Sidi Bel Abbès",
    23: "Annaba",
    24: "Guelma",
    25: "Constantine",
    26: "Médéa",
    27: "Mostaganem",
    28: "M'Sila",
    29: "Mascara",
    30: "Ouargla",
    31: "Oran",
    32: "El Bayadh",
    33: "Illizi",
    34: "Bordj Bou Arreridj",
    35: "Boumerdès",
    36: "El Tarf",
    37: "Tindouf",
    38: "Tissemsilt",
    39: "El Oued",
    40: "Khenchela",
    41: "Souk Ahras",
    42: "Tipaza",
    43: "Mila",
    44: "Aïn Defla",
    45: "Naâma",
    46: "Aïn Témouchent",
    47: "Ghardaïa",
    48: "Relizane",
    49: "Timimoun",
    50: "Bordj Badji Mokhtar",
    51: "Ouled Djellal",
    52: "Béni Abbès",
    53: "In Salah",
    54: "In Guezzam",
    55: "Touggourt",
    56: "Djanet",
    57: "El M'Ghair",
    58: "El Meniaa",
    59: "Aflou",
    60: "Barika",
    61: "Ksar Chellala",
    62: "Messaad",
    63: "Aïn Oussera",
    64: "Bou Saâda",
    65: "El Abiodh Sidi Cheikh",
    66: "El Kantara",
    67: "Bir El Ater",
    68: "Ksar El Boukhari",
    69: "El Aricha",
}

ALGERIAN_WILAYAS = list(WILAYA_CODE_TO_NAME.values())
ALGERIAN_WILAYAS_LIST = ALGERIAN_WILAYAS


def _normalize_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


ALGERIAN_WILAYAS_NORMALIZED = {
    _normalize_key(name): name for name in ALGERIAN_WILAYAS
}
ALGERIAN_WILAYAS_NORMALIZED.update(
    {
        "algiers": "Alger",
        "setif": "Sétif",
        "bejaia": "Béjaïa",
        "bechar": "Béchar",
        "saida": "Saïda",
        "msila": "M'Sila",
        "ain defla": "Aïn Defla",
        "ain temouchent": "Aïn Témouchent",
        "beni abbes": "Béni Abbès",
        "el mghair": "El M'Ghair",
        "bou saada": "Bou Saâda",
    }
)


def get_wilaya_name(code: Union[int, str]) -> Optional[str]:
    """Return the canonical name for a wilaya code, or None if it is unknown."""
    try:
        numeric_code = int(code)
    except (TypeError, ValueError):
        return None
    return WILAYA_CODE_TO_NAME.get(numeric_code)


def get_wilaya_code(name: str) -> Optional[int]:
    """Return the code for a wilaya name or supported alias, or None if unknown."""
    if not isinstance(name, str) or not name.strip():
        return None
    normalized = _normalize_key(name)
    canonical_name = ALGERIAN_WILAYAS_NORMALIZED.get(normalized)
    if canonical_name is None:
        return None
    return next(
        code for code, wilaya_name in WILAYA_CODE_TO_NAME.items()
        if wilaya_name == canonical_name
    )


def is_valid_wilaya(value: Union[str, int]) -> bool:
    """Check a wilaya name or code against the canonical 69-wilaya list."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value in WILAYA_CODE_TO_NAME
    return get_wilaya_code(value) is not None


def normalize_wilaya(name: str) -> str:
    """Return the canonical name for a wilaya name or preserve unknown input."""
    if not isinstance(name, str):
        return name
    return ALGERIAN_WILAYAS_NORMALIZED.get(_normalize_key(name), name.strip())
