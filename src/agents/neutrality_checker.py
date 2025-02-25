from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger

client = OpenAI(api_key=config.openai.api_key)

class TermReplacement(BaseModel):
    non_neutral_term: str
    alternative_term: str

class ListOfTerms(BaseModel):
    term_list: list[TermReplacement]

class NeutralityChecker:
    def __init__(self):
        pass
    
    def get_neutral_alternatives(self, text: str) -> ListOfTerms:
        initial_list = self._request_neutral_alternatives(text)
        sanitized_list = self._guardrail_ensure_existing_terms(text,initial_list)
        StreamlitLogger.log(f"Non-neutral language and alternatives: {sanitized_list}")
        return sanitized_list

    def _request_neutral_alternatives(self, text: str) -> ListOfTerms:
        """Use GPT-4o to check for neutrality."""
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You prioritize important issues rather than being pedantic over language usage."},
                {"role": "user", "content": f"Output a JSON list of non-neutral terms with a suggested alternative neutral wording for the following text. The alternative term may be an empty string if the non-neutral term is superfluous. Output an empty list if everything is in a neutral tone or if there are no big issues. Do not report the non-neutral term if there are no neutral alternatives. The text starts now: \n\n{text}"}
            ],
            response_format=ListOfTerms,
        )
        return response.choices[0].message.parsed
    
    def _guardrail_ensure_existing_terms(self, text :str, term_list :ListOfTerms) -> ListOfTerms:
        idx = 0
        while idx < len(term_list):
            term :TermReplacement = term_list[idx]

            if not (term.non_neutral_term in text):
                # remove term if it wasn't found in original text
                print(f"Term '{term.non_neutral_term}' with replacement '{term.alternative_term}' was not found in original text.")
                term_list.pop(idx)
                
            else:
                # only increment if no erause
                idx += 1

        return term_list

        

