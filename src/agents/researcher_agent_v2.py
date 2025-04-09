from anthropic import Anthropic
from pydantic import BaseModel
from src.config.settings import config
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
from src.utils.helpers import parse_to_mediawiki, parse_to_streamlit
from src.utils.wikitext_patcher import WikitextPatcher
import difflib

client = Anthropic(api_key=config.anthropic.api_key)

# Surrounding context length
LEN_CTX = 60
def generate_diff_context(text, i1, i2):
    return f"...{text[max(i1-LEN_CTX,0):i1]}<b>{text[i1:i2]}</b>{text[i2:min(i2+LEN_CTX,len(text))]}..."


class ResearcherAgentV2:
    def __init__(self, topic: str, research_text_b64: str, plaintext_article: str):
        self.topic: str = topic
        self.document: str = research_text_b64
        self.plaintext_article: str = plaintext_article

        self.mwparsed_response: str = None

        self.response: str = None
    
    def summarize_source(self) -> str:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system="You are a Wikipedia editor. Follow Wikipedia's neutral tone and style, and do not make up information that is not in the presented documents.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": self.document
                            },
                            "title": "User-submitted document",
                            "context": "This is a trustworthy document.",
                            "citations": {"enabled": True}
                        },
                        {
                            "type": "text",
                            #"text":f"In bullet point form, extract information of encyclopedic value including but not limited to metrics and dates, that is related to the topic of '{self.topic}' in the text that will follow. It must relate to '{self.topic}' in some form."
                            "text": "Using the document provided as a source, improve the current article with information of encyclopedic value. This is including but not limited to metrics and dates, that is related to the topic of '{self.topic}' Write NEW sentences inside the article. You may reword information from the summary, but avoid changing existing text in the article too much. Answer with ONLY the new article. The following is the current article to edit:\n{self.text}"
                        }
                    ]
                }
            ]
        )


        self.mwparsed_response = parse_to_mediawiki(response)
        #print(response)
        return response
    
    def get_diff_suggestions(self) -> list[Suggestion]:
        THRESHOLD = 10  # Adjust this threshold as needed

        matcher = difflib.SequenceMatcher(None, self.text, self.mwparsed_response)
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
                        text=f"Replace <b>'{matcher.a[i1:i2]}'</b> with <b>'{matcher.b[j1:j2]}'</b>",
                        patch=void_func,
                        context=generate_diff_context(matcher.a,i1,i2),
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
                if not matcher.a[i1:i2].strip():
                    return
                new_suggestion = Suggestion(
                    type=f"Edit (ContentEditor, with source {self.index})",
                    text=f"Insert <b>'{matcher.a[i1:i2]}'</b>",
                    patch=void_func,
                    context=generate_diff_context(matcher.b,j1,j2),
                )
                suggestion_list.append(new_suggestion)
                #return '**`' + matcher.b[j1:j2] + '`**'
                return
            StreamlitLogger.log(f"[ContentEditor{self.index}] Unknown tag {tag} while diff-ing.")
            return
        [process_tag(*t) for t in merged]
        return suggestion_list