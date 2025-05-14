"""
pdf_tools.py  –  fixed
======================

plan_to_json(plan_number) → dict with Table-5 JSON.

• Spawns mavat_mcp.py over stdio on each call (fast: the PDF download dominates)
• Calls the MCP tool get_plan_pdf via mcp.client.stdio
• Saves the PDF, extracts Table-5, asks GPT-4o to turn TSV → JSON
"""

import asyncio
import base64
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from extract_table5 import (
    find_table5_page,
    extract_widest_table,
    table_to_tsv,
    tsv_to_json_via_chat,
)


# ---------------------------------------------------------------------------
# Helper: download PDF bytes (base-64 string) from the MCP server
# ---------------------------------------------------------------------------
async def _get_plan_pdf_b64_async(plan_number: str) -> str:
    """Call the MCP server’s get_plan_pdf tool and return its base-64 bytes."""
    server = StdioServerParameters(command="python", args=["mavat_mcp.py"])

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_plan_pdf", {"plan_number": plan_number}
            )

    # result.content[0].text holds the base-64 PDF string
    return result.content[0].text


def _download_pdf_b64(plan_number: str) -> str:
    """Sync wrapper around the async download helper."""
    return asyncio.run(_get_plan_pdf_b64_async(plan_number))


# ---------------------------------------------------------------------------
# High-level tool exposed to AutoGen
# ---------------------------------------------------------------------------
def plan_to_json(plan_number: str) -> dict:
    """
    Download the MaVaT PDF for `plan_number` and return Table-5 JSON.
    """
    # 1) download & save PDF
    pdf_b64 = _download_pdf_b64(plan_number)
    pdf_path = Path(f"{plan_number}.pdf").resolve()
    pdf_path.write_bytes(base64.b64decode(pdf_b64))

    # 2) extract Table-5 TSV
    page = find_table5_page(pdf_path)
    table = extract_widest_table(page)
    tsv = table_to_tsv(table)

    # 3) GPT-4o: TSV → JSON
    return tsv_to_json_via_chat(tsv)


# ---------------------------------------------------------------------------
# Tools we export to main_a2a.py
# ---------------------------------------------------------------------------
TOOL_MAP = {
    "plan_to_json": plan_to_json,
    "get_plan_pdf": _download_pdf_b64,   # optional: raw download tool
}
