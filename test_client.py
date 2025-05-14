"""
Smoke-test the `mavat_mcp.py` server on Windows.

Usage:
    python test_client.py <PLAN_NUMBER>
"""

from __future__ import annotations

import asyncio
import base64
import sys
import warnings
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# 1) Optional: keep the console free of GC chatter about closed pipes
# ──────────────────────────────────────────────────────────────────────────────
warnings.filterwarnings("ignore", category=ResourceWarning)

# 2) MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(plan_number: str) -> None:
    # 3) Launch the MCP server in a child process (stdio transport)
    server = StdioServerParameters(command="python", args=["mavat_mcp.py"])

    async with stdio_client(server) as (read_stream, write_stream):
        # 4) Open a protocol session and perform the handshake
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 5) Call the tool
            result = await session.call_tool(
                "get_plan_pdf", {"plan_number": plan_number}
            )

        # ⬆️ Leaving ClientSession closes the JSON-RPC channel politely.
    # ⬆️ Leaving stdio_client waits for the child process to exit.

    # 6) Decode and save the returned PDF
    pdf_bytes = base64.b64decode(result.content[0].text)
    out_path = Path(f"{plan_number}.pdf").resolve()
    out_path.write_bytes(pdf_bytes)
    print(f"✅  Saved {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python test_client.py <PLAN_NUMBER>")
    asyncio.run(main(sys.argv[1]))
