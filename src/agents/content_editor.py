from openai import OpenAI
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import extract_context_from_words
import difflib
from src.utils.wikitext_patcher import WikitextPatcher

# Surrounding context length
LEN_CTX = 60

SMALLER_LEN_CTX = 20

# unused
class EditType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"

# unused
class Edit(BaseModel):
    type: EditType
    context_before: Optional[str] # the words preceding it
    content: Optional[str] = None  # For added or removed changes
    original_content: Optional[str] = None  # For modified changes
    modified_content: Optional[str] = None  # For modified changes

def generate_diff_context(text, i1, i2):
    return f"...{text[max(i1-LEN_CTX,0):i1]}<b>{text[i1:i2]}</b>{text[i2:min(i2+LEN_CTX,len(text))]}..."

def generate_diff_context_clean(text, i1, i2):
    return f"{text[max(i1-SMALLER_LEN_CTX,0):i1]}<b>{text[i1:i2]}</b>{text[i2:min(i2+SMALLER_LEN_CTX,len(text))]}"

class ContentEditor:
    def __init__(self, topic: str, article_text, summary_missing, idx):
        self.topic: str = topic
        self.text: str = article_text
        self.summary = summary_missing
        self.index = idx
        self.response: str = None
        self.client = OpenAI(api_key=config.openai.api_key)

        self.conversation_context = []

    def continue_conversation(self, original_suggestion: Suggestion, user_input: str) -> Suggestion:
        # create a new context
        new_conversation_context = list(self.conversation_context)
        # refine prompt
        new_conversation_context.append(
            {
                "role": "user",
                "content": f"The user wants clarification on the suggestion to \"{original_suggestion.text}\" in your edited article. The following is their comment: \"{user_input}\". Provide a short reasoning that responds directly to the user."
            }
        )
        response = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=new_conversation_context
        )

        new_suggestion = Suggestion(
                type=original_suggestion.type,
                text=original_suggestion.text,
                patch=original_suggestion.patch,
                callback=original_suggestion.callback,
                context=f"{original_suggestion.context}<br><br>>User: {user_input}<br>Reasoning: {response.choices[0].message.content}"
            )
        print(new_suggestion, flush=True)

        return new_suggestion
    
    def improve_article_with_missing_info(self) -> str:
        """Use GPT-4o to improve content based on analysis."""

        messages_prompt = [
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You focus on adding missing information rather than rewording existing information in the article."},
                {"role": "user", "content": f"Given a summary of a different source and our current article, edit the current article to include all information contained in the summary, placing the information in the relevant place. Write NEW sentences inside the article. You may reword information from the summary, but avoid changing existing text in the article too much. Answer with ONLY the new article. Here is the summary:\n{self.summary}\n\n\nSUMMARY ENDS HERE. The following is the current article to edit:\n{self.text}"}
            ]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=messages_prompt
        )
        self.response = response.choices[0].message.content
        # Save the conversation context for refinement later
        messages_prompt.append(response.choices[0].message)
        self.conversation_context = list(messages_prompt)

        return response.choices[0].message.content
    
    def get_diff_suggestions(self) -> list[Suggestion]:
        THRESHOLD = 10  # Adjust this threshold as needed

        matcher = difflib.SequenceMatcher(None, self.text, self.response)
        opcodes = matcher.get_opcodes()
        # Merge nearby opcodes
        merged = []
        i = 0
        n = len(opcodes)
        
        while i < n:
            # Check if current, next, and next+1 opcodes form a change-equal-change pattern
            if i + 2 < n:
                op1 = opcodes[i]
                op2 = opcodes[i+1]
                op3 = opcodes[i+2]
                # Ensure the middle opcode is 'equal' and the others are changes
                if op1[0] != 'equal' and op2[0] == 'equal' and op3[0] != 'equal':
                    a_len_equal = op2[2] - op2[1]
                    b_len_equal = op2[4] - op2[3]
                    # Check if the equal segment is short enough in either a or b
                    if a_len_equal <= THRESHOLD or b_len_equal <= THRESHOLD:
                        # Merge the three opcodes into one
                        new_a_start = op1[1]
                        new_a_end = op3[2]
                        new_b_start = op1[3]
                        new_b_end = op3[4]
                        a_length = new_a_end - new_a_start
                        b_length = new_b_end - new_b_start
                        # Determine the merged tag
                        if a_length > 0 and b_length > 0:
                            new_tag = 'replace'
                        elif a_length > 0:
                            new_tag = 'delete'
                        else:
                            new_tag = 'insert'
                        merged.append((new_tag, new_a_start, new_a_end, new_b_start, new_b_end))
                        i += 3  # Skip the processed opcodes
                        continue
            # If no merge, add the current opcode and move forward
            merged.append(opcodes[i])
            i += 1

        suggestion_list = []

        def void_func():
                return

        def process_tag(tag, i1, i2, j1, j2):
            if tag == 'replace':
                if (not matcher.a[i1:i2].strip()) and (not matcher.b[j1:j2].strip()):
                    return
                
                # pseudo-insert
                if (not matcher.a[i1:i2].strip()):
                    tag = 'insert'

                # pseudo-delete
                elif (not matcher.b[j1:j2].strip()):
                    tag = 'delete'


                else:
                    new_suggestion = Suggestion(
                        type=f"Edit (ContentEditor, with source {self.index})",
                        text=f"Replace <b>'{matcher.a[i1:i2]}'</b><br>with <b>'{matcher.b[j1:j2]}'</b>",
                        patch=WikitextPatcher.create_text_replacement_patch(matcher.a[i1:i2],matcher.b[j1:j2]),
                        callback=self,
                        context=f"<br><br><b>Original surrounding:</b> {generate_diff_context(matcher.a,i1,i2)}<br><b>New surrounding:</b> {generate_diff_context(matcher.b,j1,j2)}",
                    )
                    suggestion_list.append(new_suggestion)
                    #return '~~`' + matcher.a[i1:i2] + '`~~**`' + matcher.b[j1:j2] + '`**'
                    return
            if tag == 'delete':
                if not matcher.a[i1:i2].strip():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Delete <b>'{matcher.a[i1:i2]}'</b>",
                    patch=WikitextPatcher.create_text_replacement_patch(matcher.a[i1:i2],""),
                    callback=self,
                    context=f"<br><br><b>Original surrounding:</b> {generate_diff_context(matcher.a,i1,i2)}<br><b>New surrounding:</b> {generate_diff_context(matcher.b,j1,j2)}",
                )
                suggestion_list.append(new_suggestion)
                #return '~~`' + matcher.a[i1:i2] + '`~~'
                return
            if tag == 'equal':
                return
                #return matcher.a[i1:i2]
            if tag == 'insert':
                if not matcher.a[i1:i2].strip():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Insert <b>'{matcher.a[i1:i2]}'</b>",
                    patch=WikitextPatcher.create_text_replacement_patch(
                        generate_diff_context_clean(matcher.a,i1,i2),
                        generate_diff_context_clean(matcher.b,j1,j2)
                        ),
                    callback=self,
                    context=f"<br><br><b>Original surrounding:</b> {generate_diff_context(matcher.a,i1,i2)}<br><b>New surrounding:</b> {generate_diff_context(matcher.b,j1,j2)}",
                )
                suggestion_list.append(new_suggestion)
                #return '**`' + matcher.b[j1:j2] + '`**'
                return
            StreamlitLogger.log(f"[ContentEditor{self.index}] Unknown tag {tag} while diff-ing.")
            return
        [process_tag(*t) for t in merged]
        return suggestion_list