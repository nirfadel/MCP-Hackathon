"""
extract_table5.py  –  resilient version
---------------------------------------
• Works even if the table is an embedded image (vision fallback)
• Maps fuzzy / variant Hebrew headers to *canonical* 9 keys
• Missing values come back as null (not an empty list)

Canonical keys returned (order is whatever the PDF uses):
    שם התכנית ייעוד תא שטח
    סה"כ מ"ר
    שטח תכסית )%(
    הפקעה )מ"ר(
    שטח למבנה ציבור )מ"ר(
    סה"כ שטח בניה )מ"ר(
    קומות מעל הקרקע
    קומות מתחת הקרקע
    רחק
"""
from __future__ import annotations
import base64, json, re, warnings
from pathlib import Path
from typing import List

import pdfplumber
from PIL import Image
from openai import AzureOpenAI

# ── 1. Azure creds ────────────────────────────────────────────────────────────
AZURE_OAI_ENDPOINT = "https://ai-tomgurevich0575ai135301545538.openai.azure.com"
AZURE_OAI_KEY      = "EM7HLeBTOHSNHTTPG1mYWUyHyJNZuyXM3VIW01taczzBp4ottOioJQQJ99BEACHYHv6XJ3w3AAAAACOGQ0fz"
AZURE_OAI_VERSION  = "2025-01-01-preview"
DEPLOYMENT_NAME    = "gpt-4o"

client = AzureOpenAI(
    api_key        = AZURE_OAI_KEY,
    api_version    = AZURE_OAI_VERSION,
    azure_endpoint = AZURE_OAI_ENDPOINT,
)

# ── 2. PDF helpers ────────────────────────────────────────────────────────────
warnings.filterwarnings("ignore", message="CropBox missing")

REV_KEYWORDS = ("תלבט", "הינב", "יזוחא")   # טבלת / בניה / אחוזי (backwards)
REV_MOZEA    = ("עצומ", "בצמ")             # מוצע backwards

def find_table5_page(pdf_path: Path) -> pdfplumber.page.Page:
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            txt = (page.extract_text() or "").replace(" ", "")
            if all(k in txt for k in REV_KEYWORDS) and any(m in txt for m in REV_MOZEA):
                return page
    raise RuntimeError("Table-5 page not found")

def extract_widest_table(page) -> List[List[str]]:
    tables = page.extract_tables()
    if not tables:
        raise RuntimeError("No text tables on that page")
    return max(tables, key=lambda t: len(t[0]))

def table_to_tsv(table) -> str:
    return "\n".join("\t".join(cell or "" for cell in row) for row in table)


# ── 3. GPT prompt – canonical-or-fallback ─────────────────────────────────────
CANON = [
    "שם התכנית ייעוד תא שטח",
    "סה\"כ מ\"ר",
    "שטח תכסית )%(",
    "הפקעה )מ\"ר(",
    "שטח למבנה ציבור )מ\"ר(",
    "סה\"כ שטח בניה )מ\"ר(",
    "קומות מעל הקרקע",
    "קומות מתחת הקרקע",
    "רחק",
]

SYS = (
    "קח/י את ה-TSV המצורף והחזר/י מערך JSON.\n"
    "עליך למפות כל כותרת בטבלה לכותרת הקנונית המתאימה (להלן) לפי משמעות. "
    "אם כותרת קנונית לא קיימת, בחר/י כותרת אחרת בטבלה שמתאימה ביותר "
    "והשתמש/י בשמה המקורי. אל תחזיר/י ערך null.\n"
    "רשימת הכותרות הקנוניות:\n"
    + "\n".join("• " + h for h in CANON) +
    "\nהחזר/י JSON נקי בלבד."
)


USER = (
    "להלן הטבלה ב-TSV (TAB מפריד | שורה ראשונה כותרות). "
    "המר/י אותה לפי ההנחיות.\n\n{tsv}"
)

def tsv_to_json(tsv: str) -> list:
    resp = client.chat.completions.create(
        model           = DEPLOYMENT_NAME,
        response_format = {"type": "json_object"},
        messages=[
            {"role": "system", "content": SYS},
            {"role": "user",   "content": USER.format(tsv=tsv)},
        ],
        temperature=0,
        max_tokens=2048,
    )
    reply = resp.choices[0].message.content.strip()
    if reply.startswith("```"):
        reply = re.sub(r"^```(?:json)?\s*", "", reply)
        reply = re.sub(r"\s*```$", "", reply)
    return json.loads(reply)

tsv_to_json_via_chat = tsv_to_json


# ── 4. OCR/vision fallback when table is an image ─────────────────────────────
def tsv_from_image(page) -> str:
    img_bytes = page.to_image(resolution=300).original.stream.getvalue()
    b64 = base64.b64encode(img_bytes).decode()
    vision_msg = [
        {"role": "system",
         "content": "Extract TSV (TAB between cells, NEWLINE between rows) "
                    "from the Hebrew table in the image. Output *only* TSV."},
        {"role": "user",
         "content": [
             {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
             {"type": "text", "text": "טבלת זכויות – מצב מוצע"}]}
    ]
    resp = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=vision_msg,
        temperature=0,
        max_tokens=2048,
    )
    return resp.choices[0].message.content.strip()

# ── 5. Public helper for pipeline --------------------------------------------
def extract_table5_json(pdf_path: Path) -> list:
    page = find_table5_page(pdf_path)
    try:
        tsv = table_to_tsv(extract_widest_table(page))
    except RuntimeError:
        tsv = tsv_from_image(page)
    return tsv_to_json(tsv)

# ── 6. CLI test ---------------------------------------------------------------
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) != 2:
        sys.exit("Usage: python extract_table5.py <PDF_PATH>")
    result = extract_table5_json(Path(sys.argv[1]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
