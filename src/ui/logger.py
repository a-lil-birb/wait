from typing import Callable

# Shared logger to allow agents to log to the UI

class StreamlitLogger:
    _log_callback: Callable[[str], None] = None
    
    @classmethod
    def initialize(cls, callback: Callable[[str], None]):
        cls._log_callback = callback
        
    @classmethod
    def log(cls, message: str):
        if cls._log_callback:
            cls._log_callback(message)
        else:
            print(f"Fallback Log: {message}")  # For CLI/debugging