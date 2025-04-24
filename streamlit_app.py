import streamlit as st
import streamlit.components.v1 as components
from src import core
from src.utils.wikipedia import WikipediaClient
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
import time
from enum import Enum
from typing import Dict, Callable
from bs4 import BeautifulSoup
import requests
from src.utils.helpers import wikitext_to_plaintext, wikitext_to_plaintext_skip_tables_refs
from pathlib import Path
import json

# Initialize logger with Streamlit callback
def setup_logger():
    def streamlit_log(message: str):
        if 'log' not in st.session_state:
            st.session_state.log = []

        timestamp = time.strftime("%H:%M:%S")
        entry = f"{timestamp} - {message}"

        st.session_state.log.append(entry)

        if 'log_container' in st.session_state:
            with st.session_state.log_container:
                st.code(entry)
    
    StreamlitLogger.initialize(streamlit_log)

setup_logger()

# Configuration - stores keys in ~/.streamlit_secrets.json
SECRETS_PATH = Path.home() / ".streamlit_secrets.json"

def load_secrets():
    """Load saved secrets from local file"""
    try:
        return json.loads(SECRETS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}

def save_secrets():
    """Save current secrets to local file"""
    SECRETS_PATH.write_text(json.dumps({
        "OPENAI_API_KEY": st.session_state.openai_key,
        "ANTHROPIC_API_KEY": st.session_state.anthropic_key
    }, indent=2))

# Initialize session state with saved secrets
if 'secrets_initialized' not in st.session_state:
    secrets = load_secrets()
    st.session_state.openai_key = secrets["OPENAI_API_KEY"]
    st.session_state.anthropic_key = secrets["ANTHROPIC_API_KEY"]
    st.session_state.secrets_initialized = True

def api_key_manager():
    """API key input form with persistent storage"""
    with st.expander("🔑 API Key Management", expanded=False):
        with st.form("api_keys_form"):
            st.markdown("Enter your API keys:")
            
            new_openai = st.text_input(
                "OpenAI API Key", 
                value=st.session_state.openai_key,
                type="password",
                help="Get yours from https://platform.openai.com/api-keys"
            )
            
            new_anthropic = st.text_input(
                "Anthropic API Key",
                value=st.session_state.anthropic_key,
                type="password",
                help="Get yours from https://console.anthropic.com/settings/keys"
            )

            if st.form_submit_button("Save keys"):
                st.session_state.openai_key = new_openai.strip()
                st.session_state.anthropic_key = new_anthropic.strip()
                save_secrets()
                st.success("Keys updated!")

class AnalysisFlow(Enum):
    SOURCE_IMPROVEMENT = "Analyze Sources and Improve"
    LANGUAGE_NEUTRALITY = "Check Language Neutrality"
    IMPROVE_LINKING = "Improve Hyperlinking"

# Initialize Wikipedia Client
wiki = WikipediaClient()
st.set_page_config(page_title="WAIT Editor", layout="wide")

# Session state initialization
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'log' not in st.session_state:
    st.session_state.log = []
if 'active_flow' not in st.session_state:
    st.session_state.active_flow = None
if 'flow_status' not in st.session_state:
    st.session_state.flow_status = {}

# Display final output based on accepted suggestions
# Add to session state initialization
if 'history' not in st.session_state:
    st.session_state.history = {
        'wikitext': [""],
        'suggestions': [[]]
    }

if 'current_wikitext' not in st.session_state:
    st.session_state.current_wikitext = ""

# Flow registry and handlers
FLOW_REGISTRY: Dict[AnalysisFlow, Callable] = {
    flow: None for flow in AnalysisFlow  # Auto-register all enum members
}

def register_flow(flow: AnalysisFlow):
    def decorator(func: Callable):
        FLOW_REGISTRY[flow] = func
        return func
    return decorator

@register_flow(AnalysisFlow.SOURCE_IMPROVEMENT)
def handle_source_improvement(article_title: str, sources: list, urls: list, original_content: str, wikitext_content: str):
    #try:
    StreamlitLogger.log("Starting source analysis...")

    if len(sources) < 1:
        StreamlitLogger.log("No sources were submitted. Please upload at least one source to use this flow.")
        return {"status": "error", "suggestions": []}
    
    StreamlitLogger.log("Processing sources...")
    #source_url_data = [url.strip() for url in urls if url.strip()]
    source_summaries = core.summarize_sources(article_title, original_content, wikitext_content, sources)

    st.session_state.summaries = source_summaries
    
    # use a special table-less version for this one
    original_content = wikitext_to_plaintext_skip_tables_refs(wikitext_content)
    
    enhancement_suggestions = core.enhance_with_source_summaries(article_title, original_content, wikitext_content, source_summaries)
    
    return {
        "status": "success",
        "suggestions": enhancement_suggestions
    }
    #except Exception as e:
    #    StreamlitLogger.log(f"Error: {str(e)}")
    #    return {"status": "error"}
    
@register_flow(AnalysisFlow.LANGUAGE_NEUTRALITY)
def handle_neutrality_improvement(article_title: str, sources: list, urls: list, original_content: str, wikitext_content: str):
    try:
        StreamlitLogger.log("Starting language neutrality analysis...")
        
        StreamlitLogger.log("Generating suggestions...")
        enhancement_suggestions = core.check_neutrality(article_title, original_content, wikitext_content)
        
        return {
            "status": "success",
            "suggestions": enhancement_suggestions
        }
    except Exception as e:
        StreamlitLogger.log(f"Error: {str(e)}")
        return {"status": "error"}
    
@register_flow(AnalysisFlow.IMPROVE_LINKING)
def handle_linking_improvement(article_title: str, sources: list, urls: list, original_content: str, wikitext_content: str):
    try:
        StreamlitLogger.log("Starting article hyperlinking improvement...")
        
        StreamlitLogger.log("Generating suggestions...")
        enhancement_suggestions = core.improve_linking(article_title, original_content, wikitext_content)
        
        return {
            "status": "success",
            "suggestions": enhancement_suggestions
        }
    except Exception as e:
        StreamlitLogger.log(f"Error: {str(e)}")
        return {"status": "error"}

# Sidebar for inputs
with st.sidebar:
    api_key_manager()
    st.divider()
    st.header("Article Input")
    article_title = st.text_input("Wikipedia Article Title", "Cormorant-class gunvessel")
    if st.button("Load Article"):
        og_src = wiki.get_article_page_source(article_title)
        st.session_state.history = {
            'wikitext': [og_src],
            'suggestions': [[]]
        }

        st.session_state.current_wikitext = og_src
        StreamlitLogger.log(f"Loaded article '{article_title}'!")

    sources = st.file_uploader("Upload Source Documents", 
                             type=["pdf"],
                             accept_multiple_files=True)
    #urls = st.text_input("Source URLs (comma-separated)", "")
    urls = ""
    

def show_processing_log():
    st.subheader("Processing Log")
    with st.container(height=400):
        log_container = st.empty()
        with log_container.container():
            for message in st.session_state.log:
                st.code(message, language="text", wrap_lines=True)

def render_flow_buttons():
    cols = st.columns(len(FLOW_REGISTRY))
    for idx, (flow, _) in enumerate(FLOW_REGISTRY.items()):
        with cols[idx]:
            if st.button(flow.value):
                st.session_state.active_flow = flow
                st.session_state.flow_status[flow] = {
                    "running": True,
                    "result": None
                }

def process_active_flow():
    if st.session_state.active_flow:
        # Validate flow exists in registry
        if st.session_state.active_flow not in FLOW_REGISTRY:
            #StreamlitLogger.log(f"Invalid flow: {st.session_state.active_flow}")
            st.session_state.active_flow = None
            return

        flow = st.session_state.active_flow
        handler = FLOW_REGISTRY[flow]
        flow_status = st.session_state.flow_status.get(flow, {})
        
        # Only process if not completed
        if not flow_status.get('completed'):
            with st.status(f"Running {flow.value}...", expanded=True) as status:
                if flow_status.get('running', False):
                    try:
                        
                        # replace with current content if exists
                        if st.session_state.current_wikitext == "":
                            original_content = wiki.get_article_plain_text(article_title)
                            original_wikitext_content = wiki.get_article_page_source(article_title)
                        else:
                            original_content = wikitext_to_plaintext(st.session_state.current_wikitext)
                            original_wikitext_content = st.session_state.current_wikitext

                        result = handler(
                            article_title,
                            sources,
                            [url.strip() for url in urls.split(",")] if urls else [],
                            original_content,
                            original_wikitext_content
                        )
                        st.session_state.flow_status[flow] = {
                            "running": False,
                            "completed": True,
                            "result": result
                        }
                        
                        if result["status"] == "success":
                            st.session_state.suggestions = result["suggestions"]
                            
                    except Exception as e:
                        StreamlitLogger.log(f"Error in {flow.value}: {str(e)}")
                        st.session_state.flow_status[flow] = {
                            "running": False,
                            "completed": False,
                            "result": {"status": "error"}
                        }
                    st.rerun()
                else:
                    # Initialize flow run
                    st.session_state.flow_status[flow] = {
                        'running': True,
                        'completed': False
                    }
                    st.rerun()

# Main interface
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Article Analysis")
    render_flow_buttons()
    process_active_flow()
    show_processing_log()

# Initialize session state for summaries
if 'summaries' not in st.session_state:
    st.session_state.summaries = []

if 'summaries' in st.session_state and st.session_state.summaries:
    st.header("Document Summaries")

    for idx, summary in enumerate(st.session_state.summaries):

        with st.expander(f"Document #{idx+1}", expanded=True):
            col1, col2 = st.columns([2, 2])

            with col1:
                st.markdown(summary[0])
            with col2:
                st.markdown('<br><br>'.join(summary[1]), unsafe_allow_html=True)


## suggestions

# Initialize session state for suggestions
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = []

# Suggestions rendering
if 'suggestions' in st.session_state and st.session_state.suggestions:
    st.header("Improvement Suggestions")
    
    for idx, suggestion in enumerate(st.session_state.suggestions):
        suggestion_id = suggestion.id
        expander_key = f"expander_{suggestion_id}"
        refine_key = f"refine_{suggestion_id}"
        
        if f"refine_{suggestion_id}" not in st.session_state:
            st.session_state[f"refine_{suggestion_id}"] = False

        with st.expander(f"Suggestion #{idx+1}: {suggestion.type}", expanded=True):
            col1, col2 = st.columns([4, 2])
            
            with col1:
                st.markdown(f"""
                {suggestion.text.replace("\n", " ")}
                <em>{suggestion.context.replace("\n", " ")}</em>
                """, unsafe_allow_html=True)
                
            with col2:
                status_container = st.empty()
                
                # Current status display
                if suggestion.status == 'accepted':
                    status_container.success("✅ Accepted")
                elif suggestion.status == 'rejected':
                    status_container.error("❌ Rejected")
                else:
                    status_container.info("🔄 Pending")

                # Button group
                btn_col1, btn_col2, btn_col3 = st.columns([1,1,1])
                
                with btn_col1:
                    if st.button("Accept", key=f"accept_{suggestion_id}"):
                        st.session_state.suggestions[idx].status = 'accepted'
                        st.rerun()
                        
                with btn_col2:
                    if st.button("Reject", key=f"reject_{suggestion_id}"):
                        st.session_state.suggestions[idx].status = 'rejected'
                        st.rerun()
                        
                with btn_col3:
                    if st.button("Refine", key=f"refine_btn_{suggestion_id}"):
                        st.session_state[refine_key] = not st.session_state[refine_key]
                        st.session_state.suggestions[idx].status = 'pending'
                        st.rerun()

            # Refine input area
            if st.session_state[refine_key]:
                refinement = st.text_area(
                    "Enter refinement instructions:",
                    key=f"refine_input_{suggestion_id}",
                    placeholder="Ask for clarification or alternatives..."
                )
                if st.button("Submit Refinement", key=f"refine_submit_{suggestion_id}"):

                    # Get user input and original suggestion
                    user_input = st.session_state[f"refine_input_{suggestion_id}"]
                    original_suggestion = st.session_state.suggestions[idx]
                    
                    # Show loading state
                    with st.spinner("Generating refinement..."):
                        # Call LLM conversation function
                        #print(original_suggestion.callback)
                        #print(original_suggestion.callback.continue_conversation, flush=True)
                        refined_suggestion = original_suggestion.callback.continue_conversation(
                            original_suggestion=original_suggestion,
                            user_input=user_input
                        )
                        #print(refined_suggestion, flush=True)
                        
                        # Preserve original ID and status
                        refined_suggestion.id = original_suggestion.id
                        refined_suggestion.status = original_suggestion.status
                        
                        # Update the suggestion in the list
                        st.session_state.suggestions[idx] = refined_suggestion
                        
                        # Close refinement interface
                        st.session_state[refine_key] = False
                        st.rerun()
                            
                 

# Modified apply_suggestions function
def apply_suggestions(wikitext: str, apply=True) -> str:
    """Apply accepted suggestions to wikitext"""
    # Store previous state
    st.session_state.history['wikitext'].append(wikitext)
    st.session_state.history['suggestions'].append(
        [s for s in st.session_state.suggestions]
    )
    
    # Apply patches
    modified = wikitext
    if apply:
        for suggestion in st.session_state.suggestions:
            if suggestion.status == 'accepted':
                modified = suggestion.patch(modified)
                print("patching")
        
        print("patched",flush=True)
    return modified

def revert_changes():
    """Revert to previous state"""
    if st.session_state.history['wikitext']:
        st.session_state.current_wikitext = st.session_state.history['wikitext'].pop()
        st.session_state.suggestions = st.session_state.history['suggestions'].pop()

# In your final output section
st.divider()
st.header("Version Control")

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("Submit Approved Changes"):
        
        # Save current version before applying changes
        previous = st.session_state.current_wikitext
        new_content = apply_suggestions(previous)
        st.session_state.current_wikitext = new_content
        st.success("Changes submitted to history!")

with col2:
    if st.button("Save Current Changes"):
        
        # Save current version before applying changes
        previous = st.session_state.current_wikitext
        new_content = apply_suggestions(previous, apply=False)
        st.session_state.current_wikitext = new_content
        st.success("Changes submitted to history!")

with col3:
    if st.session_state.history['wikitext']:
        versions = [f"Version {i+1}" for i in range(len(st.session_state.history['wikitext']))]
        selected_version = st.selectbox("History", options=versions, index=len(versions)-1)
        
        if st.button("Revert to Selected Version"):
            idx = versions.index(selected_version)
            st.session_state.current_wikitext = st.session_state.history['wikitext'][idx]
            st.session_state.suggestions = st.session_state.history['suggestions'][idx]
            # Truncate history to selected version
            st.session_state.history['wikitext'] = st.session_state.history['wikitext'][:idx+1]
            st.session_state.history['suggestions'] = st.session_state.history['suggestions'][:idx+1]
            st.rerun()

def update_wikitext():
    st.session_state.current_wikitext = st.session_state.current_wikitext_box

# Display current wikitext
st.text_area("Wikipedia-formatted Content",
             value=st.session_state.current_wikitext,
             height=400,
             key="current_wikitext_box",
             on_change=update_wikitext)

#if st.button("state_history"):
#    st.session_state.history
#if st.button("suggestions"):
#    st.session_state.suggestions
#if st.button("current_wikitext"):
#    st.session_state.current_wikitext
if st.button("Render Wikitext"):
    # Convert Wikitext to HTML using Wikipedia API
    response = requests.post(
        'https://en.wikipedia.org/w/api.php',
        data={
            'action': 'parse',
            'format': 'json',
            'text': st.session_state.current_wikitext,
            'contentmodel': 'wikitext',
        }
    )

    if response.status_code == 200:
        result = response.json()
        html = result['parse']['text']['*']
        
        # Convert relative links to absolute
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all(['a', 'img']):
            if tag.get('href'):
                if tag['href'].startswith('/'):
                    tag['href'] = f'https://en.wikipedia.org{tag["href"]}'
            if tag.get('src'):
                if tag['src'].startswith('//'):
                    tag['src'] = f'https:{tag["src"]}'
                elif tag['src'].startswith('/'):
                    tag['src'] = f'https://en.wikipedia.org{tag["src"]}'

        processed_html = str(soup)
        st.markdown("### Rendered Content:")
        st.html(processed_html)
    else:
        st.error("Error converting Wikitext. Please try again.")


if __name__ == "__main__":
    st.session_state.processing = False