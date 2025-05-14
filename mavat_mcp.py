"""
An MCP server that exposes a single `get_plan_pdf` tool.

How it works
------------
* We wrap your Playwright routine in an MCP *tool* so that LLM agents
  (or any MCP client) can discover and invoke it.
* The tool returns the PDF as a Base-64 string so it remains JSON-serialisable.
* You can launch the server over:
    • stdio  (perfect for local dev or Docker “exec” style usage)
    • streamable-http  (good for remote deployment behind an HTTPS proxy)
------------------------------------------------------------------------
Requires:
    pip install "mcp[cli]" playwright
    playwright install chromium
"""

import asyncio
import base64
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# ---------------------------------------------------------------------
# Create an MCP server object (name + semver are just metadata)
# ---------------------------------------------------------------------
mcp = FastMCP(
    name="Mavat Plan-PDF",
    version="0.1.0",
    instructions=(
        "This server lets you download raw PDF documents for statutory "
        "plans listed in Israel's MaVaT planning portal. Call the "
        "`get_plan_pdf` tool with a numeric plan identifier."
    ),
)

# ---------------------------------------------------------------------
# Tool: get_plan_pdf
# ---------------------------------------------------------------------
@mcp.tool()
async def get_plan_pdf(plan_number: str) -> str:
    """
    Download the raw PDF for a given MaVaT plan number.

    Args
    ----
    plan_number : str
        The numeric plan identifier as it appears in MaVaT.

    Returns
    -------
    str
        The PDF encoded as a base-64 string.  (Clients typically write it
        straight to disk after `base64.b64decode`.)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        target = f"https://mavat.iplan.gov.il/SV3?text={plan_number}"

        try:
            await page.goto(target, wait_until="load", timeout=30_000)
        except PWTimeoutError:
            # Some MaVaT pages are slow – we continue anyway.
            pass

        await page.wait_for_timeout(1_000)

        # MaVaT sometimes bounces back to SV3; go “Back” if that happens.
        if page.url != target:
            await page.go_back(wait_until="load", timeout=10_000)
            await page.wait_for_timeout(500)

        # Open accordion panes & click the PDF icon (same xpath you had).
        await page.click("div.uk-accordion-title:has-text('מסמכי התכנית')")
        await page.wait_for_timeout(300)
        await page.click("div.uk-accordion-title.title-b:has-text('מסמכים בתהליך')")
        await page.wait_for_timeout(300)
        await page.click("span.uk-text-lead:has-text('הוראות')")
        await page.wait_for_timeout(300)

        async with page.expect_download(timeout=20_000) as dl_info:
            await page.click('img.sv4-icon-file.pdf-download[title="ראה קובץ בפורמט PDF"]')

        download = await dl_info.value
        path: str | None = await download.path()
        if not path:
            raise RuntimeError("Download failed – MaVaT did not return a file.")

        pdf_bytes = Path(path).read_bytes()

        # 🡆 Return as base-64 text for easy transport over MCP JSON-RPC.
        return base64.b64encode(pdf_bytes).decode()

# ---------------------------------------------------------------------
# Entrypoint – choose your transport.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Mavat MCP server")
    parser.add_argument(
        "--http", action="store_true", help="Serve over streamable-http on :8080/mcp"
    )
    args = parser.parse_args()

    if args.http:
        # Stateless HTTP is easiest to deploy behind nginx / Caddy
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
    else:
        # Default: stdio (perfect for `mcp dev` or inspector)
        mcp.run()  # same as mcp.run(transport="stdio")
