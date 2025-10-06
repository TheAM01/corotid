#!/usr/bin/env python3
"""
Universal Job Scraper - Pure OpenAI Agents SDK
ZERO hardcoded selectors or patterns
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from agents import Agent, Runner
from pure_agents.orchestrator import create_orchestrator_agent
from pure_agents.tools import BrowserTool, LLMAnalysisTool
from utils.logger import setup_logger
import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError

load_dotenv()
logger = setup_logger(__name__)


# Add retry decorator for rate limits
def with_rate_limit_handling(func):
    return retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True
    )(func)

class UniversalJobScraper:
    def __init__(self):
        self.browser_tool = None
        self.llm_tool = None
        self.orchestrator = None
        # self.runner = None
        
    async def initialize(self):
        """Initialize pure agent system"""
        logger.info("Initializing AI Job Scraper with Pure Agents")
        
        # Initialize tools
        self.browser_tool = BrowserTool()
        self.llm_tool = LLMAnalysisTool()
        
        await self.browser_tool.initialize()
        
        # Create orchestrator agent
        self.orchestrator = create_orchestrator_agent(
            browser_tool=self.browser_tool,
            llm_tool=self.llm_tool
        )
        
        # Create runner
        # self.runner = Runner()
        
        logger.info("AI Job Scraper initialized")
        
    def get_user_input(self):
        """Get job search parameters"""
        print("\n=== AI Job Scraper ===")
        print("This system takes assistance from AI to scrape jobs.\n")
        
        job_title = input("Job Title: ").strip()
        while not job_title:
            job_title = input("Job Title (required): ").strip()
            
        company_name = input("Company Name: ").strip()
        company_domain = input("Company Domain (if known): ").strip()
        
        while not company_name and not company_domain:
            print("Provide at least company name OR domain!")
            company_name = input("Company Name: ").strip()
            if not company_name:
                company_domain = input("Company Domain: ").strip()
                
        location = input("Location (optional): ").strip()
        
        return {
            "job_title": job_title,
            "company_name": company_name if company_name else None,
            "company_domain": company_domain if company_domain else None,
            "location": location if location else None
        }
        
    async def scrape_jobs(self, job_params):
        """Scrape jobs with rate limit handling"""
        logger.info(f"Starting universal scrape: {job_params}")
        
        max_retries = 3
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                initial_message = f"""
    I need to scrape job information:
    - Job Title: {job_params['job_title']}
    - Company: {job_params.get('company_name') or job_params.get('company_domain')}
    - Location: {job_params.get('location') or 'Any'}

    Find ALL matching jobs. Extract complete information.
    """
                
                result = await Runner.run(self.orchestrator, initial_message, max_turns=50)
    
                final_output = result.final_output if hasattr(result, 'final_output') else str(result)
                
                try:
                    parsed_result = json.loads(final_output)
                except:
                    parsed_result = final_output
                
                output = {
                    "success": True,
                    "job_params": job_params,
                    "result": parsed_result  # Now properly parsed
                }
                
                with open("output.json", "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
                    
                logger.info("Scraping completed")
                return output
                
            except Exception as e:
                error_msg = str(e)
                
                if "rate_limit" in error_msg.lower() or "429" in error_msg:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    
                    if attempt == max_retries - 1:
                        raise Exception("Rate limit exceeded after all retries")
                else:
                    logger.error(f"Scraping failed: {error_msg}")
                    raise
            
    async def cleanup(self):
        """Cleanup resources"""
        if self.browser_tool:
            await self.browser_tool.cleanup()

async def main():
    scraper = UniversalJobScraper()
    
    try:
        await scraper.initialize()
        
        job_params = scraper.get_user_input()
        
        print("\nStarting intelligent scraping...")
        print("The agent will analyze and adapt to any website structure.")
        
        result = await scraper.scrape_jobs(job_params)
        
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETED")
        print(f"{'='*60}")
        
        if result.get("success"):
            print(f"Results saved to: output.json")
            print(f"Check the file for complete job data.")
        else:
            print(f"Error occurred. Check output.json for details.")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}")
        
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())