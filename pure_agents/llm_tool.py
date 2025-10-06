"""
LLM Analysis Tool - Agents use this to analyze content
"""

import os
import json
from openai import AsyncOpenAI
from agents import function_tool
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LLMAnalysisTool:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def get_analyze_tool(self):
        @function_tool
        async def analyze_content(content: str, question: str) -> str:
            """Ask LLM to analyze HTML/text content and answer a question"""
            try:
                prompt = f"""Analyze this content and answer the question.

Content: {content[:15000]}

Question: {question}

Provide a clear, actionable answer."""
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0.1
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                return f"Analysis failed: {str(e)}"
        return analyze_content
        
    def get_extract_links_tool(self):
        @function_tool
        async def extract_links(content: str, criteria: str) -> str:
            """Extract links from HTML matching criteria"""
            try:
                from bs4 import BeautifulSoup
                import json
                soup = BeautifulSoup(content, 'html.parser')
                
                for tag in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path', 'img', 'video']):
                    tag.decompose()
                
                cleaned_html = str(soup)[:30000]
                
                # Also extract all links as fallback
                all_links = []
                for a in soup.find_all('a', href=True):
                    all_links.append({
                        'url': a['href'],
                        'text': a.get_text(strip=True)[:100],
                        'parent_text': a.parent.get_text(strip=True)[:200] if a.parent else ""
                    })
                
                prompt = f"""Find ALL job posting links matching: "{criteria}"

    HTML content:
    {cleaned_html}

    Look for:
    - Links in job cards/listings
    - "Apply", "View details", "Learn more" buttons near job titles
    - Links with job titles in nearby text

    All links found on page (use these if they match):
    {json.dumps(all_links[:30], indent=2)}

    Return JSON array:
    [{{"url": "full URL", "job_title": "inferred job title from context"}}]

    IMPORTANT: 
    - Return actual URLs from the page
    - Include ALL matching jobs
    - Return ONLY valid JSON, no explanation"""
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                result = response.choices[0].message.content.strip()
                
                # Log raw response
                logger.info(f"LLM raw response: {result[:500]}")
                
                # Try to parse
                import json
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        logger.info(f"Successfully extracted {len(parsed)} job links")
                        return json.dumps(parsed)
                    else:
                        logger.warning(f"LLM returned non-array: {type(parsed)}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {str(e)}, Response: {result[:200]}")
                
                # If parsing fails, return empty array
                logger.warning("Returning empty array due to parsing failure")
                return "[]"
                
            except Exception as e:
                logger.error(f"Link extraction exception: {str(e)}")
                return "[]"
        return extract_links


    def get_extract_data_tool(self):
        @function_tool
        async def extract_data(content: str, schema: str) -> str:
            """Extract structured data from content based on schema"""
            try:
                # Clean HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                for tag in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path', 'img', 'video']):
                    tag.decompose()
                
                cleaned = str(soup)[:30000]
                
                prompt = f"""Extract data from this content according to the schema.

    Content:
    {cleaned}

    Schema/Fields to extract: {schema}

    Return ONLY a JSON object with the requested fields. Set fields to null if not found.
    Example format: {{"title": "...", "location": "...", "description": "...", ...}}"""
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Data extraction failed: {str(e)}")
                return "{}"
        return extract_data