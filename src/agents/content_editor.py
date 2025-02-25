from openai import OpenAI
from src.config.settings import config

client = OpenAI(api_key=config.openai.api_key)

class ContentEditor:
    def generate_edit(self, text: str, instructions: str) -> str:
        """Use GPT-4 to improve content based on analysis."""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style."},
                {"role": "user", "content": f"Improve this text: {text}\n\nInstructions: {instructions}"}
            ]
        )
        return response.choices[0].message.content