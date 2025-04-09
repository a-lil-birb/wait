from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import extract_context_from_words
from src.utils.wikitext_patcher import WikitextPatcher

client = OpenAI(api_key=config.openai.api_key)

class TermReplacement(BaseModel):
    non_neutral_term: str
    alternative_term: str
    reasoning: str

class ListOfTerms(BaseModel):
    term_list: list[TermReplacement]

class NeutralityChecker:
    def __init__(self):
        self.cached_term_list = None
        self.conversation_context = None

    def continue_conversation(self, original_suggestion: Suggestion, user_input: str) -> Suggestion:
        if self.conversation_context is None:
            StreamlitLogger.log("Attemped to continue non-existing conversation.")
            return
        
        # create a new context
        new_conversation_context = list(self.conversation_context)
        # refine prompt
        new_conversation_context.append(
            {
                "role": "user",
                "content": f"The user wants clarification on the suggestion to \"{original_suggestion.extra[0]}\" with \"{original_suggestion.extra[1]}\". The following is their comment: \"{user_input}\". For the specified suggestion, provide an updated edit suggestion that does not change the non-neutral term but may change the alternative replacement. Provide a reasoning that responds directly to the user."
            }
        )
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=new_conversation_context,
            response_format=TermReplacement,
        )

        return response.choices[0].message.parsed
    
    def get_neutral_alternatives(self, text: str) -> ListOfTerms:
        if not (self.cached_term_list is None):
            return self.cached_term_list

        initial_list_container = self._request_neutral_alternatives(text)
        sanitized_list_container = self._guardrail_ensure_existing_terms(text,initial_list_container)
        StreamlitLogger.log(f"Non-neutral language and alternatives: {sanitized_list_container.term_list}")
        
        self.cached_term_list = sanitized_list_container.term_list

        return sanitized_list_container.term_list

    def get_suggestions(self, text: str) -> list[Suggestion]:
        
        if self.cached_term_list is None:
            StreamlitLogger.log("empty suggestion cache")
            return []
        
        suggestion_list = []
        for term in self.cached_term_list:
            term: TermReplacement

            original_sentence: str = extract_context_from_words(text,term.non_neutral_term)[0]
            new_sentence = original_sentence.replace(term.non_neutral_term,term.alternative_term)

            new_suggestion = Suggestion(
                type="Non-neutral language",
                text=f"Replace <b>'{term.non_neutral_term}'</b> with <b>'{term.alternative_term}'</b>",
                patch=WikitextPatcher.create_text_replacement_patch(term.non_neutral_term,term.alternative_term),
                context=f"{original_sentence}\nReasoning:{term.reasoning}",
                extra=[self.continue_conversation, term.non_neutral_term, term.alternative_term, term.reasoning]
            )
            suggestion_list.append(new_suggestion)

        return suggestion_list
    
    

    def _request_neutral_alternatives(self, text: str) -> ListOfTerms:
        """Use GPT-4o to check for neutrality."""

        messages_prompt = [
            {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You prioritize important issues rather than being pedantic over language usage."},
            {"role": "user", "content": f"Output a JSON list of non-neutral terms with a suggested alternative neutral wording for the following text. The alternative term may be an empty string if the non-neutral term is superfluous. Output an empty list if everything is in a neutral tone or if there are no big issues. Do not report the non-neutral term if there are no neutral alternatives. Provide a reasoning for each change. The text starts now: \n\n{text}"}
            ]

        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=messages_prompt,
            response_format=ListOfTerms,
        )

        self.conversation_context = messages_prompt.append(response.choices[0].message)
        return response.choices[0].message.parsed
    
    def _guardrail_ensure_existing_terms(self, text :str, term_list_container :ListOfTerms) -> ListOfTerms:
        idx = 0
        while idx < len(term_list_container.term_list):
            term :TermReplacement = term_list_container.term_list[idx]

            if not (term.non_neutral_term in text):
                # remove term if it wasn't found in original text
                StreamlitLogger.log(f"[Guardrail] Term '{term.non_neutral_term}' with replacement '{term.alternative_term}' was not found in original text.")
                term_list_container.term_list.pop(idx)
                
            else:
                # only increment if no erause
                idx += 1

        return term_list_container