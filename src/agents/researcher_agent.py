from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion



class ResearcherAgent:
    def __init__(self, topic: str, research_text: str):
        self.topic: str = topic
        self.text: str = research_text
        self.response: str = None
        self.client = OpenAI(api_key=config.openai.api_key)
    
    def summarize_source(self) -> str:
        """Use GPT-4 to improve content based on analysis."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style, and do not make up information that is not in the presented documents."},
                {"role": "user", "content": f"In bullet point form, extract information of encyclopedic value including but not limited to metrics and dates, that is related to the topic of '{self.topic}' in the text that will follow. It must relate to '{self.topic}' in some form. The text starts now:\n\n{self.text}"}
            ]
        )
        self.response = response.choices[0].message.content

        return response.choices[0].message.content



        

