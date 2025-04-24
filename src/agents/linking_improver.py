from openai import OpenAI
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import extract_context_from_words, strip_code_block, get_wikipedia_link
from src.utils.wikitext_patcher import WikitextPatcher
from src.utils.wikipedia import WikipediaClient
import json


class TermToLink(BaseModel):
    term_to_link: str
    article: str
    reasoning: str

class ListOfTerms(BaseModel):
    term_list: list[TermToLink]

class LinkingImprover:
    def __init__(self, topic: str, wikitext: str):
        self.topic: str = topic
        self.wikitext :str = wikitext
        self.cached_term_list = None
        self.conversation_context = []
        self.wiki_client = WikipediaClient()
        self.client = OpenAI(api_key=config.openai.api_key)

    def get_wiki_article_preview_tool(self, title: str):
        data = self.wiki_client.exists_article(title)
        exists = data['exists']
        excerpt = data['excerpt']

        if exists:
            return f"Article '{title}' exists. Short excerpt: {excerpt}."
        else:
            return f"Article '{title}' does not exist."

    def continue_conversation(self, original_suggestion: Suggestion, user_input: str) -> Suggestion:
        # create a new context
        new_conversation_context = list(self.conversation_context)
        # refine prompt
        new_conversation_context.append(
            {
                "role": "user",
                "content": f"On the Wikipeda article {self.topic}, the user wants clarification on the suggestion to link the text \"{original_suggestion.extra[0]}\" to the article \"{original_suggestion.extra[1]}\". The following is their comment: \"{user_input}\". For the specified suggestion, provide an updated edit suggestion that does not change the text to be linked. Provide a reasoning that responds directly to the user."
            }
        )
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=new_conversation_context,
            response_format=TermToLink,
        )

        term: TermToLink = response.choices[0].message.parsed
        print(term, flush=True)

        replacement = ""
        if term.term_to_link == term.article:
            replacement = f"[[{term.term_to_link}]]"
        else:
            replacement = f"[[{term.article}|{term.term_to_link}]]"

        new_suggestion = Suggestion(
                type="Add hyperlinking",
                text=f"Link <b>'{term.term_to_link}'</b> to article <b>'[{term.article}]({get_wikipedia_link(term.article)})'</b>",
                patch=WikitextPatcher.create_text_replacement_patch(term.term_to_link,replacement),
                callback=self,
                context=f"{original_suggestion.context}<br><br>>User: {user_input}<br><b>Reasoning:</b> {term.reasoning}",
                extra=[term.term_to_link,term.article,term.reasoning]
            )
        print(new_suggestion, flush=True)

        return new_suggestion
    
    def execute_flow(self) -> ListOfTerms:
        if not (self.cached_term_list is None):
            return self.cached_term_list

        initial_list = self._request_additional_linking()
        sanitized_list = self._guardrail_ensure_existing_terms(self.wikitext,initial_list)
        StreamlitLogger.log(f"Linking improvements: {sanitized_list}")
        
        self.cached_term_list = sanitized_list

        return sanitized_list

    def get_suggestions(self) -> list[Suggestion]:
        
        if self.cached_term_list is None:
            StreamlitLogger.log("empty suggestion cache")
            return []
        
        suggestion_list = []
        print(f"gen suggestions, {self.conversation_context}", flush=True)
        for term in self.cached_term_list:

            original_sentence: str = extract_context_from_words(self.wikitext,term["term_to_link"])[0]
            #new_sentence = original_sentence.replace(term.non_neutral_term,term.alternative_term)
            replacement = ""
            if term['term_to_link'] == term['article']:
                replacement = f"[[{term['term_to_link']}]]"
            else:
                replacement = f"[[{term['article']}|{term['term_to_link']}]]"

            new_suggestion = Suggestion(
                type="Add hyperlinking",
                text=f"Link <b>'{term['term_to_link']}'</b> to article <b>'[{term['article']}]({get_wikipedia_link(term['article'])})'</b>",
                patch=WikitextPatcher.create_text_replacement_patch(term['term_to_link'],replacement),
                callback=self,
                context=f"<br><b>Featured in this sentence:</b> {original_sentence}.<br><b>Reasoning:</b> {term['reasoning']}",
                extra=[term['term_to_link'],term['article'],term['reasoning']]
            )
            suggestion_list.append(new_suggestion)

        return suggestion_list
    
    def _run_until_completion(self, run, thread, assistant):
        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            print(messages, flush=True)
            print(messages.data[0].content[0].text.value, flush=True)
            return strip_code_block(messages.data[0].content[0].text.value)
        else:
            print(run.status, flush=True)

        # Define the list to store tool outputs
        tool_outputs = []
        
        # Loop through each tool in the required action section
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "get_wiki_article_preview_tool":
                print(f"MW Search tool with arg {tool.function.arguments}", flush=True)

                args = json.loads(tool.function.arguments)
                output = self.get_wiki_article_preview_tool(args['title'])
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": output
                })
            else:
                print("Unknown tool", flush=True)
        
        # Submit all tool outputs at once after collecting them in a list
        if tool_outputs:
            StreamlitLogger.log(f"Tool outputs: {tool_outputs}")
            try:
                run = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
                )
                print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)
        else:
            ("No tool outputs to submit.")

        return self._run_until_completion(run,thread,assistant)
    

    def _request_additional_linking(self):
        """Use GPT-4o to check for neutrality."""

        assistant = self.client.beta.assistants.create(
            instructions="You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You want to improve readability of articles by linking to other article in-text when appropriate.",
            model="gpt-4o-mini-2024-07-18",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_wiki_article_preview_tool",
                        "description": "Check whether or not an article with the supplied title exists. If it exists, also returns a short preview to see if it is relevant.",
                        "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the article to search."
                            }
                        },
                        "required": ["title"],
                        "additionalProperties": False
                        },
                        "strict": True
                    }
                },
            ]
        )

        thread = self.client.beta.threads.create()
        message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"In order to improve readability, Wikipedia articles may link to other Wikipedia articles for completeness on a topic. The syntax is [[Title]] where Title is the linked article, or [[Title|Appearance]] where the term Appearance links to article Title. Identify terms that are not previously linked anywhere on the article, and that would benefit from being linked from article topic {self.topic}. Use the provided 'get_wiki_article_preview_tool' to check if an article exists, and if the article is appropriate, before linking. Provide a reasoning for each change. Format the output as ONLY a JSON list containing objects as such: [{{'term_to_link':'string','article':'string','reasoning':'string'}},...] where 'term_to_link' is the term found in text, 'article' is the name of the article it should link to, and 'reasoning' is the reasoning for doing so. The MediaWiki-formatted text starts now: \n\n{self.wikitext}",
        )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        output = self._run_until_completion(run,thread,assistant)
        #StreamlitLogger.log(output)
        correct_output = self._guardrail_ensure_valid_json_output(output)

        if not correct_output:
            return self._request_additional_linking()
        
        return json.loads(output)
    
    def _guardrail_ensure_valid_json_output(self, output):
        passed = True
        try:
            list_of_terms = json.loads(output)

            for term in list_of_terms:
                if "term_to_link" in term and "article" in term and "reasoning" in term:
                    pass
                else:
                    StreamlitLogger.log("Invalid JSON output from linking improver.")
                    print("Invalid JSON output from linking improver.")
                    passed = False
            pass
        except ValueError:
            StreamlitLogger.log("Invalid JSON output from linking improver.")
            print("Invalid JSON output from linking improver.")
            passed = False

        return passed

    def _guardrail_ensure_existing_terms(self, text :str, term_list) -> ListOfTerms:
        idx = 0
        while idx < len(term_list):
            term = term_list[idx]

            if not (term["term_to_link"] in text):
                # remove term if it wasn't found in original text
                StreamlitLogger.log(f"[Guardrail] Term '{term["term_to_link"]}' was not found in original text.")
                term_list.pop(idx)
            elif f"{term["term_to_link"]}]]" in text:
                StreamlitLogger.log(f"[Guardrail] Term '{term["term_to_link"]}' already has a hyperlink.")
                term_list.pop(idx)
            elif f"[[{term["term_to_link"]}" in text:
                StreamlitLogger.log(f"[Guardrail] Term '{term["term_to_link"]}' is already a hyperlinked article.")
                term_list.pop(idx)
                
            else:
                # only increment if no erasure
                idx += 1

        return term_list