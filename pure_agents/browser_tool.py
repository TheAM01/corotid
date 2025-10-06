"""
Browser Tool - Playwright interface for agents
Tools that agents can call to control browser
"""
import re
import asyncio
from playwright.async_api import async_playwright
from agents import function_tool
from utils.logger import setup_logger

logger = setup_logger(__name__)

class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    async def initialize(self):
        """Start browser"""
        logger.info("Initializing browser")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            slow_mo=100,
            args=['--no-sandbox']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1600, 'height': 900}
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        logger.info("Browser ready")
        
    def get_navigate_tool(self):
        @function_tool
        async def navigate_to_url(url: str) -> str:
            """Navigate browser to URL"""
            try:
                if not url.startswith(('http://', 'https://')):
                    url = f"https://{url}"
                await self.page.goto(url, wait_until='domcontentloaded')
                await asyncio.sleep(1)
                return f"Navigated to {self.page.url}"
            except Exception as e:
                return f"Navigation failed: {str(e)}"
        return navigate_to_url
        
    def get_content_tool(self):
        @function_tool
        async def get_page_content() -> str:
            """Get current page HTML content"""
            try:
                html = await self.page.content()
                
                # Clean HTML before returning
                from bs4 import BeautifulSoup, Comment
                soup = BeautifulSoup(html, 'html.parser')
                
                for tag in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path', 'img', 'video']):
                    tag.decompose()
                
                cleaned = str(soup)[:25000]  # Now can use larger limit since it's cleaner
                return cleaned
                
            except Exception as e:
                return f"Error: {str(e)}"
        return get_page_content
        
    def get_click_tool(self):
        @function_tool
        async def click_element(element_description: str) -> str:
            """Click element described in natural language. Agent will use LLM to find it first."""
            try:
                # Get page content for LLM analysis
                html = await self.page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for tag in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path', 'img', 'video']):
                    tag.decompose()
                cleaned_html = str(soup)
                # Import LLM tool here to avoid circular dependency
                from openai import AsyncOpenAI
                import os
                
                client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                prompt = f"""Find the element to click based on this description: "{element_description}"

Page HTML: {cleaned_html[:20000]}

Return ONLY a JSON object:
{{"selector": "CSS selector to click", "reasoning": "why this element"}}"""
                
                response = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                selector = result["selector"]
                
                await self.page.click(selector)
                await asyncio.sleep(1)
                return f"Clicked: {element_description}. New URL: {self.page.url}"
                
            except Exception as e:
                return f"Click failed: {str(e)}"
        return click_element
        
    def get_fill_tool(self):
        @function_tool
        async def fill_input(field_description: str, value: str) -> str:
            """Fill input field. LLM finds the field based on description."""
            try:
                html = await self.page.content()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                for tag in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path', 'img', 'video']):
                    tag.decompose()
                cleaned_html = str(soup)
                
                from openai import AsyncOpenAI
                import os
                
                client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                prompt = f"""Find input field: "{field_description}"

Page HTML: {cleaned_html[:20000]}

Return ONLY JSON:
{{"selector": "CSS selector for input", "reasoning": "why"}}"""
                
                response = await client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                selector = result["selector"]
                
                await self.page.fill(selector, value)
                
                # Try to submit
                try:
                    await self.page.press(selector, "Enter")
                    await asyncio.sleep(2)
                except:
                    pass
                    
                return f"Filled '{field_description}' with '{value}'"
                
            except Exception as e:
                return f"Fill failed: {str(e)}"
        return fill_input

    def get_job_iframe_tool(self, llm_tool):
        @function_tool
        async def check_and_enter_job_iframe() -> str:
            """
            Look through all iframes on the current page and let the LLM decide
            which one contains job listings. Switch the page context to that iframe.
            """

            try:
                iframes = await self.page.query_selector_all('iframe')
                if not iframes:
                    return "No iframes found"

                for i, iframe in enumerate(iframes):
                    frame = await iframe.content_frame()
                    if not frame:
                        continue

                    html = await frame.content()

                    # Ask LLM if this frame contains job listings
                    analysis = await llm_tool.get_analyze_tool()(
                        html,
                        "Does this frame contain job postings? Respond YES or NO."
                    )

                    if "yes" in analysis.lower():
                        # Switch context to this iframe for future operations
                        self.page = frame
                        return f"Switched to iframe {i} with job listings"

                return "No iframe with job listings found"

            except Exception as e:
                return f"Iframe check failed: {str(e)}"

        return check_and_enter_job_iframe


    def get_iframe_tool(self):
        @function_tool
        async def check_and_enter_iframe() -> str:
            """Check if content is in iframe and switch to it"""
            try:
                # Check for iframes
                iframes = await self.page.query_selector_all('iframe')
                
                if not iframes:
                    return "No iframes found"
                
                # Try each iframe
                for i, iframe in enumerate(iframes):
                    frame = await iframe.content_frame()
                    if frame:
                        # Get iframe content
                        content = await frame.content()
                        print(content)
                        if len(content) > 1000:  # Has substantial content
                            # Switch to this frame
                            self.page = frame
                            return f"Switched to iframe {i}, content length: {len(content)}"
                
                return "No accessible iframes with content"
                
            except Exception as e:
                return f"Iframe check failed: {str(e)}"
        return check_and_enter_iframe
        
    async def cleanup(self):
        """Close browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")