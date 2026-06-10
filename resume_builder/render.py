from pathlib import Path


async def to_pdf(html: str, path: Path) -> None:
    """Render HTML string to a PDF file via Playwright (headless Chromium).

    First-time setup: uv run playwright install chromium
    """
    from playwright.async_api import async_playwright  # lazy import

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(path=str(path), format="Letter", print_background=True)
        await browser.close()
