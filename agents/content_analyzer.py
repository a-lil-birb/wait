import spacy
from typing import Dict

class ContentAnalyzer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
    
    def analyze(self, text: str) -> Dict:
        doc = self.nlp(text)
        return {
            "readability": self._calculate_readability(doc),
            "citation_issues": self._find_citation_issues(text),
            "missing_sections": self._identify_missing_sections(doc)
        }
    
    def _calculate_readability(self, doc) -> float:
        # Simplified readability metric
        return len(doc) / (len(list(doc.sents)) + 1)
    
    def _find_citation_issues(self, text: str) -> int:
        return text.lower().count("[citation needed]")
    
    def _identify_missing_sections(self, doc) -> list:
        # Simple section analysis (expand with ML model)
        common_sections = {"history", "background", "controversies"}
        existing = {chunk.text.lower() for chunk in doc.noun_chunks}
        return list(common_sections - existing)