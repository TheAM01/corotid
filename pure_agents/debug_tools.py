from agents import function_tool
from utils.logger import setup_logger

logger = setup_logger(__name__)

def create_debug_tools():
    """Tools that log what the agent is doing"""
    
    @function_tool
    async def log_progress(step: str, details: str) -> str:
        """Log what step the agent is on"""
        logger.info(f"AGENT STEP: {step}")
        logger.info(f"DETAILS: {details}")
        print(f"\n>>> AGENT: {step}")
        print(f"    {details}")
        return f"Logged: {step}"
    
    return [log_progress]