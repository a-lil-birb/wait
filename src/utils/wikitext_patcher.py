from src.utils.helpers import find_excerpt_position
import re
from typing import Callable

class WikitextPatcher:
    @staticmethod
    def create_text_replacement_patch(original_excerpt: str, new_text: str) -> Callable[[str], str]:
        """Create patch for simple text replacements"""
        def patch(wikitext: str) -> str:
            pos = find_excerpt_position(original_excerpt, wikitext)
            print(f"{pos}",flush=True)
            if not pos:
                print("Was not patched.",flush=True)
                return wikitext
            return wikitext[:pos[0]] + new_text + wikitext[pos[1]:]
        return patch

    @staticmethod
    def create_section_patch(section_title: str, new_content: str) -> Callable[[str], str]:
        """Create patch for entire section replacements"""
        def patch(wikitext: str) -> str:
            section_pattern = rf"(\n==+ {re.escape(section_title)} ==+.*?)(?=\n==|$)"
            match = re.search(section_pattern, wikitext, re.DOTALL)
            if not match:
                return wikitext
            return wikitext.replace(match.group(1), f"\n{new_content.strip()}")
        return patch

    @staticmethod
    def create_citation_patch(context: str, citation: str) -> Callable[[str], str]:
        """Create patch for adding citations"""
        def patch(wikitext: str) -> str:
            pos = find_excerpt_position(context, wikitext)
            if not pos:
                return wikitext
            return wikitext[:pos[1]] + f"<ref>{citation}</ref>" + wikitext[pos[1]:]
        return patch