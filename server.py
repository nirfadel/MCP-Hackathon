# server.py

import io
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

app = FastAPI(title="Mavat Plan-PDF MCP Service")

@app.on_event("shutdown")
async def shutdown_event():
    # no-op to keep FastAPI happy
    await asyncio.sleep(0)

@app.get("/plan-pdf/", response_class=StreamingResponse)
async def get_plan_pdf(
    plan_number: str = Query(..., description="The numeric plan identifier")
):
    """
    Downloads the raw PDF for the given plan number and streams it back as
    application/pdf so the calling agent can save or re-process the file.
    """
    async with async_playwright() as p:
        # 1) Launch headless Chromium
        browser = await p.chromium.launch(headless=True)
        # 2) Enable downloads in this context
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        target = f"https://mavat.iplan.gov.il/SV3?text={plan_number}"
        # 3) Navigate (with a timeout guard)
        try:
            await page.goto(target, wait_until="load", timeout=30_000)
        except PWTimeoutError:
            # if it times out, we’ll proceed anyway
            pass

        # 4) Wait a bit for any JS-led redirect/render
        await page.wait_for_timeout(1_000)

        # 5) Handle the possible redirect back to SV3
        if page.url != target:
            await page.go_back(wait_until="load", timeout=10_000)
            await page.wait_for_timeout(500)

        # 6) Open the relevant accordions
        await page.click("div.uk-accordion-title:has-text('מסמכי התכנית')", timeout=10_000)
        await page.wait_for_timeout(300)
        await page.click("div.uk-accordion-title.title-b:has-text('מסמכים בתהליך')", timeout=10_000)
        await page.wait_for_timeout(300)
        await page.click("span.uk-text-lead:has-text('הוראות')", timeout=10_000)
        await page.wait_for_timeout(300)

        # 7) Trigger the download of the PDF file
        async with page.expect_download(timeout=20_000) as download_info:
            await page.click('img.sv4-icon-file.pdf-download[title="ראה קובץ בפורמט PDF"]')
        download = await download_info.value

        # 8) Read the downloaded file from disk
        path = await download.path()
        if not path:
            raise HTTPException(500, "Download failed: no file saved")
        pdf_bytes = open(path, "rb").read()

        # 9) Clean up
        await context.close()
        await browser.close()

    # 10) Stream raw PDF bytes back to caller
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{plan_number}.pdf"'},
    )
