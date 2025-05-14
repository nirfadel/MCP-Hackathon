#!/usr/bin/env python3
# ────────────────────────────────────────────────────────────────
# address_lookup.py  –  end-to-end demo: free-form address ➜ city-plans hit list
# Requires:  pip install openai==1.*  azure-identity requests
# ────────────────────────────────────────────────────────────────
import os, json, math, re, time, requests
from openai import AzureOpenAI

# ── 1. Azure OpenAI credentials (▼ put YOURS here or use env vars) ─────────────
AZURE_OAI_ENDPOINT  = os.getenv("AZURE_OAI_ENDPOINT",
    "https://ai-tomgurevich0575ai135301545538.openai.azure.com")
AZURE_OAI_KEY       = os.getenv("AZURE_OAI_KEY",
    "EM7HLeBTOHSNHTTPG1mYWUyHyJNZuyXM3VIW01taczzBp4ottOioJQQJ99BEACHYHv6XJ3w3AAAAACOGQ0fz")
AZURE_OAI_VERSION   = "2025-01-01-preview"       # supports GPT-4o func-calling
DEPLOYMENT_NAME     = "gpt-4o"                   # ⚠️ must match *deployment* name

client = AzureOpenAI(
    api_key       = AZURE_OAI_KEY,
    api_version   = AZURE_OAI_VERSION,
    azure_endpoint= AZURE_OAI_ENDPOINT,
    azure_deployment=DEPLOYMENT_NAME,            # optional; can pass per-call too
)

# ── 2. Function-calling schema for the model ───────────────────────────────────
FUNC_SCHEMA = [{
    "name":        "parse_address",
    "description": "Extract house number, street, city and country from free text",
    "parameters": {
        "type": "object",
        "properties": {
            "number":  {"type": "integer", "description": "house / building number"},
            "street":  {"type": "string",  "description": "street name"},
            "city":    {"type": "string",  "description": "municipality"},
            "country": {"type": "string",  "description": "country (default Israel)"},
        },
        "required": ["street", "city"]
    }
}]

def llm_parse_address(user_text: str) -> dict | None:
    """Return dict {'street':..., 'number':..., 'city':..., 'country':...} or None."""
    resp = client.chat.completions.create(
        model       = DEPLOYMENT_NAME,   # deployment name
        messages    = [{"role":"user", "content": f"Parse this address: {user_text}"}],
        functions   = FUNC_SCHEMA,
        function_call="auto",
        temperature = 0,                 # deterministic parsing
        max_tokens  = 50
    )
    msg = resp.choices[0].message
    if msg.function_call and msg.function_call.name == "parse_address":
        return json.loads(msg.function_call.arguments)
    return None

# ── 3. Geocoding helpers (Nominatim + Photon) ──────────────────────────────────
UA = "MCP-Geocoder/2.0 (+tom.gurevich@example.com)"   # <-- your email/contact

def _nominatim(query: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1, "addressdetails":0,
              "countrycodes": "il"}
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=10)
    if r.status_code == 429:
        time.sleep(1); r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=10)
    if r.ok:
        return r.json()
    return []

def _photon(query: str):
    url = "https://photon.komoot.io/api"
    params = {"q": query, "limit": 1, "lang": "he"}
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=10)
    if r.ok and r.json().get("features"):
        lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
        return [{"lat": str(lat), "lon": str(lon)}]
    return []

def geocode_parts(a: dict) -> tuple[float|None,float|None]:
    """Return (lat,lon) or (None,None)."""
    q = f"{a.get('street','')} {a.get('number','')}, {a['city']}, {a.get('country','Israel')}"
    hits = _nominatim(q) or _photon(q)
    if hits:
        return float(hits[0]["lat"]), float(hits[0]["lon"])
    return None, None

# ── 4. Simple Haversine distance (km) ──────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = map(math.radians, (lat1, lat2))
    dphi   = math.radians(lat2 - lat1)
    dl     = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ── 5. City-plans fetch & filter ───────────────────────────────────────────────
PLANS_URL = (
    "https://data.gov.il/dataset/city-plans-br7/"
    "resource/183c23ae-13f4-47f9-b756-184547777e00/"
    "download/city-plans.json"
)

LOCAL_JSON = "city-plans.json"   # file you just downloaded

def plans_within(lat, lon, radius_km=0.1):
    if not os.path.exists(LOCAL_JSON):
        raise FileNotFoundError(
            f"{LOCAL_JSON} not found – download it once from:\n"
            "https://data.gov.il/dataset/city-plans-br7/resource/"
            "183c23ae-13f4-47f9-b756-184547777e00/download/city-plans.json"
        )

    with open(LOCAL_JSON, "r", encoding="utf-8") as f:
        all_items = json.load(f)           # whole JSON array

    hits = [
        item for item in all_items
        if haversine(lat, lon,
                     float(item["lat"]), float(item["lon"])) <= radius_km
    ]
    pat = re.compile(r"^(\d{3}-\d{7})(?:\(\d+\))?$")  # capture core, allow optional "(…)"
    filtered = []
    for item in hits:
        m = pat.match(item["Plan"].strip())
        if m:
            item["Plan"] = m.group(1)  # keep only 605-0543108 part
            filtered.append(item)
    return filtered


# ── 6. Demo main loop ──────────────────────────────────────────────────────────
if __name__ == "__main__":
        raw = input("Enter any Israeli address (Heb/Eng): ").strip()
        if not raw:
            raise ValueError("Empty input.")

        parsed = llm_parse_address(raw)
        if not parsed:
            raise RuntimeError("LLM could not parse that address.")

        print("LLM parsed:", parsed)

        lat, lon = geocode_parts(parsed)
        if lat is None:
            raise RuntimeError("Could not geocode the parsed address.")

        print(f"Coordinates: {lat:.6f}, {lon:.6f}")

        hits = plans_within(lat, lon)
        print(f"\n▶ Found {len(hits)} city-plan record(s) within 100 m:\n")
        print(json.dumps(hits, indent=2, ensure_ascii=False))


