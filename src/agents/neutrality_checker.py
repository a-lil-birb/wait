from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import extract_context_from_words
from src.utils.wikitext_patcher import WikitextPatcher


class TermReplacement(BaseModel):
    non_neutral_term: str
    alternative_term: str
    reasoning: str

class ListOfTerms(BaseModel):
    term_list: list[TermReplacement]

class NeutralityChecker:
    def __init__(self):
        self.cached_term_list = None
        self.conversation_context = []
        self.client = OpenAI(api_key=config.openai.api_key)

    def continue_conversation(self, original_suggestion: Suggestion, user_input: str) -> Suggestion:
        # create a new context
        new_conversation_context = list(self.conversation_context)
        # refine prompt
        new_conversation_context.append(
            {
                "role": "user",
                "content": f"The user wants clarification on the suggestion to \"{original_suggestion.extra[0]}\" with \"{original_suggestion.extra[1]}\". The following is their comment: \"{user_input}\". For the specified suggestion, provide an updated edit suggestion that does not change the non-neutral term but may change the alternative replacement. Provide a reasoning that responds directly to the user."
            }
        )
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=new_conversation_context,
            response_format=TermReplacement,
        )

        term: TermReplacement = response.choices[0].message.parsed
        print(term, flush=True)

        new_suggestion = Suggestion(
                type="Non-neutral language",
                text=f"Replace <b>'{term.non_neutral_term}'</b> with <b>'{term.alternative_term}'</b>",
                patch=WikitextPatcher.create_text_replacement_patch(term.non_neutral_term,term.alternative_term),
                callback=self,
                context=f"{original_suggestion.context}<br><br>>User: {user_input}<br><b>Reasoning:</b> {term.reasoning}",
                extra=[term.non_neutral_term, term.alternative_term, term.reasoning]
            )
        print(new_suggestion, flush=True)

        return new_suggestion
    
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
        print(f"gen suggestions, {self.conversation_context}", flush=True)
        for term in self.cached_term_list:
            term: TermReplacement

            original_sentence: str = extract_context_from_words(text,term.non_neutral_term)[0]
            new_sentence = original_sentence.replace(term.non_neutral_term,term.alternative_term)

            new_suggestion = Suggestion(
                type="Non-neutral language",
                text=f"Replace <b>'{term.non_neutral_term}'</b> with <b>'{term.alternative_term}'</b>",
                patch=WikitextPatcher.create_text_replacement_patch(term.non_neutral_term,term.alternative_term),
                callback=self,
                context=f"<br><b>Featured in this sentence:</b> {original_sentence}.<br><b>Reasoning:</b> {term.reasoning}",
                extra=[term.non_neutral_term, term.alternative_term, term.reasoning]
            )
            suggestion_list.append(new_suggestion)

        return suggestion_list
    
    

    def _request_neutral_alternatives(self, text: str) -> ListOfTerms:
        """Use GPT-4o to check for neutrality."""

        messages_prompt = [
            {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You prioritize important issues rather than being pedantic over language usage."},
            {"role": "user", "content": f"Output a JSON list of non-neutral terms with a suggested alternative neutral wording for the following text. The alternative term may be an empty string if the non-neutral term is superfluous. Output an empty list if everything is in a neutral tone or if there are no big issues. Do not report the non-neutral term if there are no neutral alternatives. Provide a reasoning for each change. The text starts now: \n\n{text}"}
            ]

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=messages_prompt,
            response_format=ListOfTerms,
        )

        messages_prompt.append(response.choices[0].message)
        self.conversation_context = list(messages_prompt)
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