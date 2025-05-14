#!/usr/bin/env python3
import json
import requests
from openai import AzureOpenAI

# ── 1) Azure OpenAI credentials (hard-coded) ──────────────────────────────────
AZURE_OAI_ENDPOINT = "https://ai-tomgurevich0575ai135301545538.openai.azure.com"
AZURE_OAI_KEY      = "EM7HLeBTOHSNHTTPG1mYWUyHyJNZuyXM3VIW01taczzBp4ottOioJQQJ99BEACHYHv6XJ3w3AAAAACOGQ0fz"
AZURE_OAI_VERSION  = "2025-01-01-preview"      # supports GPT-4o + file uploads
DEPLOYMENT_NAME    = "gpt-4o"                  # your GPT-4o deployment name

client = AzureOpenAI(
    api_key        = AZURE_OAI_KEY,
    api_version    = AZURE_OAI_VERSION,
    azure_endpoint = AZURE_OAI_ENDPOINT,
)

# ── 2) Download the PDF from your MCP server ──────────────────────────────────
MCP_URL = "http://localhost:8000/plan-pdf/?plan_number=605-1288414"
pdf_bytes = requests.get(MCP_URL).content
print(f"✅ Downloaded {len(pdf_bytes):,} bytes from {MCP_URL}")

# ── 3) Ask GPT-4o to extract Table 5 as JSON ──────────────────────────────────
prompt = (
    "Extract **Table 5: טבלת זכויות והוראות בניה – מצב מוצע** from the PDF and "
    "return it as a pure JSON array of objects with keys:\n"
    "  - תא שטח\n  - גודל מגרש (מ\"ר)\n  - שטחי בניה (מ\"ר)\n  - אחוזי בניה (%)\n"
    "  - תכסית (%)\n  - מספר יח\"ד\n  - גובה מבנה (מטר)\n  - מספר קומות\n"
    "  - קו בנין (מטר)\n"
    "Return **only** that JSON—no commentary."
)

resp = client.chat.completions.create(
    model    = DEPLOYMENT_NAME,                     # must pass model
    messages = [{"role": "user", "content": prompt}],
    files    = [{"filename": "plan.pdf", "content": pdf_bytes}],
    temperature = 0,
    max_tokens  = 1000,
)

content = resp.choices[0].message.content.strip()
try:
    table5 = json.loads(content)
    print("\n📋 Parsed JSON:\n")
    print(json.dumps(table5, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print("\n⚠️  GPT-4o did not return valid JSON; raw output:\n")
    print(content)
