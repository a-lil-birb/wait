from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion


class ContentAnalyzer:
    def __init__(self, topic: str, article_text: str, provided_summary: str):
        self.topic: str = topic
        self.text: str = article_text
        self.summary: str = provided_summary
        self.response: str = None
        self.client = OpenAI(api_key=config.openai.api_key)
    
    def find_missing_information(self) -> str:
        """Use GPT-4 to improve content based on analysis."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style, and do not make up information that is not in the presented documents."},
                {"role": "user", "content": f"You will be given a summary of an external source of information, and an article about the same topic. In bullet form, while preserving all details, identify any information in the summary that is not present in the article. The summary is the following:\n{self.summary}\n\n\nTHE SUMMARY ENDS HERE. The article is the following:\n{self.text}"}
            ]
        )
        self.response = response.choices[0].message.content

        return response.choices[0].message.content



        

