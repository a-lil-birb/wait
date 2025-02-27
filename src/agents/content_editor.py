from openai import OpenAI
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import extract_context_from_words
import difflib

# Surrounding context length
LEN_CTX = 50

client = OpenAI(api_key=config.openai.api_key)

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
    return f"...{text[max(i1-LEN_CTX,0):i1]}**{text[i1:i2]}**{text[min(i2+LEN_CTX,len(text))]}..."

class ContentEditor:
    def __init__(self, topic: str, article_text, summary_missing, idx):
        self.topic: str = topic
        self.text: str = article_text
        self.summary = summary_missing
        self.index = idx
        self.response: str = None
    
    def improve_article_with_missing_info(self) -> str:
        """Use GPT-4 to improve content based on analysis."""
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {"role": "system", "content": "You are a Wikipedia editor. Follow Wikipedia's neutral tone and style. You focus on adding missing information rather than rewording existing information in the article."},
                {"role": "user", "content": f"Given a summary of a different source and our current article, edit the current article to include all information contained in the summary, placing the information in the relevant place. You may reword information from the summary, but avoid changing existing text in the article too much. Answer with ONLY the new article. Here is the summary:\n{self.summary}\n\n\nSUMMARY ENDS HERE. The following is the current article to edit:\n{self.text}"}
            ]
        )
        self.response = response.choices[0].message.content
        return response.choices[0].message.content
    
    def get_diff_suggestions(self) -> list[Suggestion]:
        matcher = difflib.SequenceMatcher(None, self.text, self.response)

        suggestion_list = []

        def void_func():
                return

        def process_tag(tag, i1, i2, j1, j2):
            if tag == 'replace':
                if matcher.a[i1:i2].isspace() and matcher.b[j1:j2].isspace():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Replace '{matcher.a[i1:i2]}' with '{matcher.b[j1:j2]}'",
                    patch=void_func,
                    context=generate_diff_context(matcher.a,i1,i2),
                )
                suggestion_list.append(new_suggestion)
                #return '~~`' + matcher.a[i1:i2] + '`~~**`' + matcher.b[j1:j2] + '`**'
                return
            if tag == 'delete':
                if matcher.a[i1:i2].isspace():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Delete '{matcher.a[i1:i2]}'",
                    patch=void_func,
                    context=generate_diff_context(matcher.a,i1,i2),
                )
                suggestion_list.append(new_suggestion)
                #return '~~`' + matcher.a[i1:i2] + '`~~'
                return
            if tag == 'equal':
                return
                #return matcher.a[i1:i2]
            if tag == 'insert':
                if matcher.b[j1:j2].isspace():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Insert '{matcher.a[i1:i2]}'",
                    patch=void_func,
                    context=generate_diff_context(matcher.b,j1,j2),
                )
                suggestion_list.append(new_suggestion)
                #return '**`' + matcher.b[j1:j2] + '`**'
                return
            StreamlitLogger.log(f"[ContentEditor{self.index}] Unknown tag {tag} while diff-ing.")
            return
        [process_tag(*t) for t in matcher.get_opcodes()]
        return suggestion_list