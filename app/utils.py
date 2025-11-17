import asyncio
from playwright.async_api import async_playwright

async def scrape_quiz_data(url: str):
    async with async_playwright() as p:
        # headless=True now, we know it works.
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1) # Extra 1s for safety
            
            # Get BOTH the clean text (for the AI)
            text_content = await page.inner_text("body")
            
            # AND the raw HTML (for our link-finder)
            html_content = await page.content()
            
            # Return both in a dictionary
            return {
                "text": text_content,
                "html": html_content
            }
            
        except Exception as e:
            return {"error": f"Error scraping page: {e}"}
            
        finally:
            await browser.close()