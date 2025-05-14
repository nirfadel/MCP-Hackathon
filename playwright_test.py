# playwright_test.py

import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://example.com")
        title = await page.title()
        print(f"Page title: {title}")
        await browser.close()

asyncio.run(run())
