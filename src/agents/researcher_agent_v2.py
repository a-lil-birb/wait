from anthropic import Anthropic
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import parse_to_mediawiki, parse_to_streamlit
from src.utils.wikitext_patcher import WikitextPatcher
import difflib


# Surrounding context length
LEN_CTX = 60
def generate_diff_context(text, i1, i2):
    return f"...{text[max(i1-LEN_CTX,0):i1]}<b>{text[i1:i2]}</b>{text[i2:min(i2+LEN_CTX,len(text))]}..."


class ResearcherAgentV2:
    def __init__(self, topic: str, research_text_b64: str, plaintext_article: str):
        self.topic: str = topic
        self.document: str = research_text_b64
        self.plaintext_article: str = plaintext_article

        self.mwparsed_response: str = None
        self.stparsed_response: str = None

        self.response: str = None
        self.client = Anthropic(api_key=config.anthropic.api_key)
    
    def summarize_source(self) -> str:
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            system="You are a Wikipedia editor. Follow Wikipedia's neutral tone and style, and do not make up information that is not in the presented documents.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": self.document
                            },
                            "title": "User-submitted document",
                            "context": "This is a trustworthy document.",
                            "citations": {"enabled": True}
                        },
                        {
                            "type": "text",
                            "text":f"In bullet point form, extract information of encyclopedic value including but not limited to metrics and dates, that is related to the topic of '{self.topic}' in the attached document. List as much as you can. It must relate to '{self.topic}' in some form. Cite the document for your points, and answer with only the bullet points. Cite for all bullet points."
                        }
                    ]
                }
            ]
        )

        print(response, flush=True)
        self.mwparsed_response = parse_to_mediawiki(response)
        self.stparsed_response = parse_to_streamlit(response)
        
        return response