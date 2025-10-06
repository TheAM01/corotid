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
            """Extract links from content matching criteria"""
            try:
                prompt = f"""Extract links from this HTML that match: "{criteria}"

HTML: {content[:15000]}

Return JSON array of objects:
[{{"url": "link URL", "text": "link text", "relevance": "why it matches"}}]

Return ONLY the JSON array, nothing else."""
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                return f"Link extraction failed: {str(e)}"
        return extract_links
        
    def get_extract_data_tool(self):
        @function_tool
        async def extract_data(content: str, schema: str) -> str:
            """Extract structured data from content based on schema"""
            try:
                prompt = f"""Extract data from this content according to the schema.

Content: {content[:15000]}

Schema/Fields to extract: {schema}

Return JSON object with the requested fields. Set fields to null if not found."""
                
                response = await self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": prompt}],
                    # temperature=0
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                return f"Data extraction failed: {str(e)}"
        return extract_data