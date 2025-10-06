"""
Orchestrator Agent - Coordinates all scraping operations
NO hardcoded logic - pure agent decisions
"""

from agents import Agent
from utils.logger import setup_logger
from .debug_tools import create_debug_tools

logger = setup_logger(__name__)

def create_orchestrator_agent(browser_tool, llm_tool):
   """Create the main orchestrator agent with all tools"""
   
   instructions = """
You are a Job Scraping Agent. Execute completely. NO questions.

TOOLS:
- navigate_to_url(url)
- get_page_content()
- analyze_content(content, question)
- click_element(description)
- fill_input(description, value)
- extract_links(content, criteria)
- extract_data(content, schema)
- log_progress(step, details)
- check_and_enter_job_iframe()

EXACT ALGORITHM - FOLLOW THIS:
STEP 1: FIND COMPANY WEBSITE
- If company_domain provided: navigate_to_url(domain) and SKIP to Step 2
- If only company_name: 
  * navigate_to_url("www.duckduckgo.com")
  * fill_input("search box", "{company_name}")
  * get_page_content()
  * extract_links to find candidate domains
  * Consider BOTH:
      - main company domain
      - subdomains containing the company name or keywords from the company name
  * Pick the domain or subdomain most likely to host the careers page; do not go to login pages
  * navigate_to_url(that domain)
  * log_progress("Found company site", url)


STEP 2: FIND CAREERS PAGE
- get_page_content()
- analyze_content(content, "What is the URL/link to the careers or jobs page?")
- Extract the careers URL from the analysis
- navigate_to_url(careers_url)
- log_progress("On careers page", careers_url)

STEP 3: FIND ALL JOB LISTINGS PAGE
- get_page_content()
- analyze_content(content, "How do I access ALL job listings? Is there a search bar, a 'View All Jobs' or 'Find a Job' link, or are listings already visible? Are the jobs in an iframe?")
- Based on answer:
  * If answer mentions iframe: call check_and_enter_job_iframe()
   - This will scan all iframes and switch context to the one containing job listings
   - Log the iframe selection
  * If search bar exists: fill_input("job search input", "{job_title}")
  * If "View All" link exists: click_element("view all jobs link")
  * If ALL listings visible: continue
- log_progress("Found job listings method", "method used")
- Wait 2-3 seconds after navigation to confirm dynamic content has loaded

STEP 4: EXTRACT MATCHING JOB LINKS
- get_page_content()
- extract_links(content, "job posting links that match title: {job_title}")
- Parse the JSON response
- log_progress("Found jobs", "count: X")

STEP 5: SCRAPE EACH JOB
- For each job URL:
  * navigate_to_url(job_url)
  * get_page_content()
  * extract_data(content, "title, company, location, description, requirements, salary, employment_type, posted_date")
  * Add to results array

STEP 6: RETURN RESULTS
- Return JSON: {"jobs": [
   {
      "title": "...",
      "company": "...",
      "location": "...",
      "description": "...",
      "requirements": "...",
      "salary": "..." or null,
      "employment_type": "...",
      "url": "...",
      "posted_date": "..."
   }
], "total_found": X, "search_query": "..."}

CRITICAL RULES:
- ONLY search DuckDuckGo ONCE in Step 1 if needed
- Do NOT search DuckDuckGo multiple times
- Follow the algorithm IN ORDER
- Use log_progress after EVERY step
- If a step fails, try ONE alternative then move on
- Extract data even if incomplete
- Wait 2-3 seconds after navigating to page to confirm all dynamic data has loaded

START NOW.
START IMMEDIATELY. NO QUESTIONS.
"""

   all_tools = [
      browser_tool.get_navigate_tool(),
      browser_tool.get_content_tool(),
      llm_tool.get_analyze_tool(),
      browser_tool.get_click_tool(),
      browser_tool.get_fill_tool(),
      llm_tool.get_extract_links_tool(),
      llm_tool.get_extract_data_tool(),
      # browser_tool.get_iframe_tool(),
      browser_tool.get_job_iframe_tool(llm_tool)
   ] + create_debug_tools()
   # Create agent with tools
   agent = Agent(
      name="UniversalScraperOrchestrator",
      instructions=instructions,
      model="gpt-5-mini",  # Use best model for complex decisions
      tools=all_tools
      # max_turns=50 
   )
   
   return agent