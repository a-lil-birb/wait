from __future__ import annotations
from enum import Enum
from typing import Callable, List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class Suggestion:
    """
    A class representing an improvement suggestion for Wikipedia content.
    
    Attributes:
        type (str): Category of the suggestion
        text (str): Human-readable description of the suggestion
        context (str): Context around the suggested material
        patch Callable[[str],str]: Function to patch the original text with the suggestion
        callback object: object of the agent so we can callback for refinements
        status (str): Current approval status; new suggestions should be 'pending'
        extra List[str]: Storing additional information, varies between agent tasks or empty list
        id (int): Unique identifier (auto-generated)
    """
    type: str
    text: str
    patch: Callable[[str],str]
    callback: object
    context: str = "Unknown"
    status: str = 'pending'
    extra: List[str] = field(default_factory=list)
    id: int = field(init=False, default_factory=lambda: Suggestion._next_id())
    
    # Class-level ID counter
    _id_counter: int = 0
    
    @classmethod
    def _next_id(cls) -> int:
        cls._id_counter += 1
        return cls._id_counter