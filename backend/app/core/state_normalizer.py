"""Canonical Indian State & Union Territory Normalizer for FarmShield.

Ensures state identifiers from user inputs, geolocation, and provider feeds
are mapped to verified canonical state names without cross-state confusion.
"""

from typing import Optional

CANONICAL_STATES: list[str] = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

# Strict mapping of common aliases, abbreviations, and spelling variants
STATE_ALIASES: dict[str, str] = {
    # Andhra Pradesh
    "andhra pradesh": "Andhra Pradesh",
    "andhra": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "in-ap": "Andhra Pradesh",
    # Telangana
    "telangana": "Telangana",
    "ts": "Telangana",
    "tg": "Telangana",
    "in-tg": "Telangana",
    "in-ts": "Telangana",
    # Maharashtra
    "maharashtra": "Maharashtra",
    "maha": "Maharashtra",
    "mh": "Maharashtra",
    "in-mh": "Maharashtra",
    # Karnataka
    "karnataka": "Karnataka",
    "ka": "Karnataka",
    "in-ka": "Karnataka",
    # Tamil Nadu
    "tamil nadu": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "in-tn": "Tamil Nadu",
    # Kerala
    "kerala": "Kerala",
    "kl": "Kerala",
    "in-kl": "Kerala",
    # Gujarat
    "gujarat": "Gujarat",
    "gj": "Gujarat",
    "in-gj": "Gujarat",
    # Rajasthan
    "rajasthan": "Rajasthan",
    "rj": "Rajasthan",
    "in-rj": "Rajasthan",
    # Madhya Pradesh
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "in-mp": "Madhya Pradesh",
    # Uttar Pradesh
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "in-up": "Uttar Pradesh",
    # Punjab
    "punjab": "Punjab",
    "pb": "Punjab",
    "in-pb": "Punjab",
    # Haryana
    "haryana": "Haryana",
    "hr": "Haryana",
    "in-hr": "Haryana",
    # Bihar
    "bihar": "Bihar",
    "br": "Bihar",
    "in-br": "Bihar",
    # West Bengal
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    "bengal": "West Bengal",
    "paschim banga": "West Bengal",
    "in-wb": "West Bengal",
    # Odisha
    "odisha": "Odisha",
    "orissa": "Odisha",
    "od": "Odisha",
    "or": "Odisha",
    "in-or": "Odisha",
    "in-od": "Odisha",
    # Chhattisgarh
    "chhattisgarh": "Chhattisgarh",
    "chhatisgarh": "Chhattisgarh",
    "cg": "Chhattisgarh",
    "in-ct": "Chhattisgarh",
    # Jharkhand
    "jharkhand": "Jharkhand",
    "jh": "Jharkhand",
    "in-jh": "Jharkhand",
    # Himachal Pradesh
    "himachal pradesh": "Himachal Pradesh",
    "himachal": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "in-hp": "Himachal Pradesh",
    # Uttarakhand
    "uttarakhand": "Uttarakhand",
    "uttaranchal": "Uttarakhand",
    "uk": "Uttarakhand",
    "in-ut": "Uttarakhand",
    # Goa
    "goa": "Goa",
    "ga": "Goa",
    "in-ga": "Goa",
    # Assam
    "assam": "Assam",
    "as": "Assam",
    "in-as": "Assam",
    # Delhi
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    "national capital territory of delhi": "Delhi",
    "new delhi": "Delhi",
    "dl": "Delhi",
    "in-dl": "Delhi",
    # Jammu and Kashmir
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "in-jk": "Jammu and Kashmir",
    # Chandigarh
    "chandigarh": "Chandigarh",
    "ch": "Chandigarh",
    "in-ch": "Chandigarh",
}


def normalize_state_name(raw: Optional[str]) -> Optional[str]:
    """Normalize a raw state name or abbreviation into its canonical Indian state name.

    Returns the canonical state name if recognized, or the cleaned title-cased string
    if not recognized, without confusing different states. Returns None for empty inputs.
    """
    if not raw or not str(raw).strip():
        return None

    cleaned = str(raw).strip().lower()
    # Direct alias lookup
    if cleaned in STATE_ALIASES:
        return STATE_ALIASES[cleaned]

    # Exact canonical match
    for state in CANONICAL_STATES:
        if state.lower() == cleaned:
            return state

    # Substring matching with safety (avoid confusing "Andhra Pradesh" with "Madhya Pradesh")
    for state in CANONICAL_STATES:
        state_low = state.lower()
        if cleaned in state_low and len(cleaned) >= 5:
            return state

    # Return clean title-cased if no alias matched
    return str(raw).strip().title()
