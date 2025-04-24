# config/settings.py
import os
from dotenv import load_dotenv
from typing import Optional
import streamlit as st  # Add Streamlit import
from src.ui.logger import StreamlitLogger

class ConfigValidationError(Exception):
    """Custom exception for configuration errors"""
    pass


class OpenAIConfig:
    def __init__(self):
        pass
        #self.api_key = os.getenv("OPENAI_API_KEY")
        
    @property
    def api_key(self):
        """Dynamically get API key from Streamlit session state"""
        if not hasattr(st.session_state, 'openai_key') or len(st.session_state.openai_key) < 10:
            StreamlitLogger.log("OpenAI API key not initialized. Use the app's key manager.")
            raise ConfigValidationError("OpenAI API key not initialized. Use the app's key manager.")
        return st.session_state.openai_key
        
class AnthropicConfig:
    def __init__(self):
        pass
        #self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
    @property
    def api_key(self):
        """Dynamically get API key from Streamlit session state"""
        if not hasattr(st.session_state, 'anthropic_key') or len(st.session_state.anthropic_key) < 10:
            StreamlitLogger.log("Anthropic API key not initialized. Use the app's key manager.")
            raise ConfigValidationError("Anthropic API key not initialized. Use the app's key manager.")
        return st.session_state.anthropic_key

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
        # Initialize session state keys if they don't exist
        if 'openai_key' not in st.session_state:
            st.session_state.openai_key = ""
        if 'anthropic_key' not in st.session_state:
            st.session_state.anthropic_key = ""

        self.openai = OpenAIConfig()
        self.anthropic = AnthropicConfig()
        self.files = FileConfig()
        self.logging = LoggingConfig()
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.requests_per_minute = int(os.getenv("RATE_LIMIT", "30"))

# Singleton instance
config = Settings()