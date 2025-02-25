# agents/__init__.py

# Import all agents for easy access
from .content_analyzer import ContentAnalyzer
#from .research_agent import ResearchAgent
from .content_editor import ContentEditor
from .neutrality_checker import NeutralityChecker
#from .fact_checker import FactCheckerAgent

# Optional: Add shared initialization code
def initialize_agents():
    """Initialize all agents with shared configurations."""
    print("Agents package initialized.")