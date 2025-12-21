import asyncio
from playwright.async_api import async_playwright

async def run():
    try:
        print("Starting Playwright...")
        async with async_playwright() as p:
            print("Playwright started.")
            browser = await p.chromium.launch(headless=True)
            print("Browser launched successfully!")
            await browser.close()
            print("Browser closed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
