"""
geo_tools.py
------------
address_to_plan(address_text) → dict with lat/lon and nearby plan numbers.
"""

from getlonlat import (
    llm_parse_address,
    geocode_parts,
    plans_within,
)


def address_to_plan(address_text: str) -> dict:
    """
    Parse a free-form Israeli address, geocode it, return nearby plan hits.

    Parameters
    ----------
    address_text : str
        Free-form address (Hebrew or English).

    Returns
    -------
    dict
        {
          "lat": float,
          "lon": float,
          "plans": [ { "Plan": "605-1288414", ... }, … ]
        }
    """
    parts = llm_parse_address(address_text)
    if not parts:
        raise ValueError("LLM failed to parse address")

    lat, lon = geocode_parts(parts)
    if lat is None:
        raise RuntimeError("Geocoder failed")

    return {"lat": lat, "lon": lon, "plans": plans_within(lat, lon)}
