# config/settings.py
import os
from dotenv import load_dotenv
from typing import Optional

class ConfigValidationError(Exception):
    """Custom exception for configuration errors"""
    pass

class WikipediaConfig:
    def __init__(self):
        self.user = os.getenv("WIKI_USER", "")
        self.password = os.getenv("WIKI_PASSWORD", "")
        self.language = os.getenv("WIKI_LANG", "en")
        self.user_agent = os.getenv("WIKI_USER_AGENT", "WAESBot/1.0 (https://example.org/waes; contact@example.org)")
        
        # Validate credentials if provided
        if self.user and not self.password:
            raise ConfigValidationError("Wikipedia password required when username is provided")

class OpenAIConfig:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        #self.model = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
        #self.temperature = float(os.getenv("OPENAI_TEMP", "0.3"))
        
        if not self.api_key:
            raise ConfigValidationError("OpenAI API key is required")
        
class AnthropicConfig:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        #self.model = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
        #self.temperature = float(os.getenv("OPENAI_TEMP", "0.3"))
        
        if not self.api_key:
            raise ConfigValidationError("Anthropic API key is required")

class FileConfig:
    def __init__(self):
        self.allowed_types = os.getenv("ALLOWED_FILE_TYPES", "pdf,txt,md,html").split(",")
        self.max_size = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default

class LoggingConfig:
    def __init__(self):
        self.level = os.getenv("LOG_LEVEL", "INFO")
        self.file_path = os.getenv("LOG_FILE", "waes.log")

# Load environment variables first
load_dotenv()

class Settings:
    def __init__(self):
        self.wiki = WikipediaConfig()
        self.openai = OpenAIConfig()
        self.anthropic = AnthropicConfig()
        self.files = FileConfig()
        self.logging = LoggingConfig()
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Rate limiting
        self.requests_per_minute = int(os.getenv("RATE_LIMIT", "30"))

# Singleton instance
config = Settings()