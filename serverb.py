import io, anyio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from playwright.sync_api import sync_playwright

app = FastAPI(title="Mavat Plan-PDF MCP Service")

def fetch_pdf(plan_number: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        pdf: bytes | None = None
        def catcher(resp):
            nonlocal pdf
            if "application/pdf" in resp.headers.get("content-type", ""):
                pdf = resp.body()

        page.on("response", catcher)
        page.goto(f"https://mavat.iplan.gov.il/SV3?text={plan_number}",
                  wait_until="networkidle")
        page.click('button[title="הצג PDF"]')
        page.wait_for_timeout(3000)
        browser.close()
        if pdf is None:
            raise RuntimeError("PDF not found")
        return pdf

@app.get("/plan-pdf/", response_class=StreamingResponse)
async def get_plan_pdf(plan_number: str = Query(...)):
    try:
        pdf_bytes = await anyio.to_thread.run_sync(fetch_pdf, plan_number)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{plan_number}.pdf\"'}
    )
