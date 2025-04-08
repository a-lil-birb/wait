from anthropic import Anthropic
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion

client = Anthropic(api_key=config.anthropic.api_key)

class ResearcherAgentV2:
    def __init__(self, topic: str, research_text_b64: str):
        self.topic: str = topic
        self.document: str = research_text_b64
        self.response: str = None
    
    def summarize_source(self) -> str:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
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
                            "text":f"In bullet point form, extract information of encyclopedic value including but not limited to metrics and dates, that is related to the topic of '{self.topic}' in the text that will follow. It must relate to '{self.topic}' in some form."
                        }
                    ]
                }
            ]
        )
        print(response)

        return response