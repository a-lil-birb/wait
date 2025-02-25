from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger

client = OpenAI(api_key=config.openai.api_key)

class ResearcherAgent:
    def __init__(self):
        pass
    
    def summarize_source(self, text: str, topic: str) -> str:
        """Use GPT-4 to improve content based on analysis."""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style."},
                {"role": "user", "content": f"In bullet point form, summarize information containing encyclopedic value for the topic of '{topic}' in the following text:\n\n{text}"}
            ]
        )
        return response.choices[0].message.content

        

