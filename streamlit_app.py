import streamlit as st
import streamlit.components.v1 as components
from src.core import enhance_article
from src import core
from src.utils.wikipedia import WikipediaClient
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
import time
from enum import Enum
from typing import Dict, Callable

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

class AnalysisFlow(Enum):
    SOURCE_IMPROVEMENT = "Analyze Sources and Improve"
    LANGUAGE_NEUTRALITY = "Check Language Neutrality"
    UNSOURCED_CLAIMS = "Identify Unsourced Claims"

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

# Flow registry and handlers
FLOW_REGISTRY: Dict[AnalysisFlow, Callable] = {
    AnalysisFlow.SOURCE_IMPROVEMENT: None,
    AnalysisFlow.LANGUAGE_NEUTRALITY: None,
    AnalysisFlow.UNSOURCED_CLAIMS: None
}

def register_flow(flow: AnalysisFlow):
    def decorator(func: Callable):
        FLOW_REGISTRY[flow] = func
        return func
    return decorator

@register_flow(AnalysisFlow.SOURCE_IMPROVEMENT)
def handle_source_improvement(article_title: str, sources: list, urls: list, original_content: str, wikitext_content: str):
    try:
        StreamlitLogger.log("Starting source analysis...")
        
        StreamlitLogger.log("Processing sources...")
        source_url_data = [url.strip() for url in urls if url.strip()]
        
        StreamlitLogger.log("Generating suggestions...")
        enhancement_suggestions = enhance_article(article_title, sources, source_url_data)
        
        return {
            "status": "success",
            "suggestions": enhancement_suggestions
        }
    except Exception as e:
        StreamlitLogger.log(f"Error: {str(e)}")
        return {"status": "error"}
    
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
    
@register_flow(AnalysisFlow.UNSOURCED_CLAIMS)
def handle_unsourcedclaims_improvement(article_title: str, sources: list, urls: list, original_content: str, wikitext_content: str):
    try:
        StreamlitLogger.log("Starting unsourced claims analysis...")
        
        StreamlitLogger.log("Generating suggestions...")
        enhancement_suggestions = core.check_neutrality(article_title, original_content, wikitext_content)
        
        return {
            "status": "success",
            "suggestions": enhancement_suggestions
        }
    except Exception as e:
        StreamlitLogger.log(f"Error: {str(e)}")
        return {"status": "error"}

# Sidebar for inputs
with st.sidebar:
    st.header("Article Input")
    article_title = st.text_input("Wikipedia Article Title", "Machine learning")
    sources = st.file_uploader("Upload Source Documents", 
                             type=["pdf", "txt", "md", "html"],
                             accept_multiple_files=True)
    urls = st.text_input("Source URLs (comma-separated)", "")

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
    if st.session_state.active_flow and FLOW_REGISTRY[st.session_state.active_flow]:
        flow = st.session_state.active_flow
        status = st.session_state.flow_status.get(flow, {})
        
        if status.get("running", False):
            with st.status(f"Running {flow.value}...", expanded=True):
                try:
                    original_content = wiki.get_article_plain_text(article_title)
                    original_wikitext_content = wiki.get_article_page_source(article_title)

                    result = FLOW_REGISTRY[flow](
                        article_title,
                        sources,
                        [url.strip() for url in urls.split(",")] if urls else [],
                        original_content,
                        original_wikitext_content
                    )
                    st.session_state.flow_status[flow] = {
                        "running": False,
                        "result": result
                    }
                    
                    if flow == AnalysisFlow.SOURCE_IMPROVEMENT and result["status"] == "success":
                        st.session_state.suggestions = result["suggestions"]
                        st.session_state.original = result["original"]
                        st.session_state.original_source = result["original_source"]
                        
                except Exception as e:
                    StreamlitLogger.log(f"Error in {flow.value}: {str(e)}")
                    st.session_state.flow_status[flow] = {
                        "running": False,
                        "result": {"status": "error"}
                    }
                st.rerun()

# Main interface
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Article Analysis")
    render_flow_buttons()
    process_active_flow()
    show_processing_log()

## suggestions

# Initialize session state for suggestions
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = []

# Function to apply accepted suggestions
def apply_suggestions(original: str) -> str:
    pass
    return original

# Suggestions rendering (same as before)
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
                <em>Context: {suggestion.context.replace("\n", " ")}</em>
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
                    st.session_state[refine_key] = False
                    st.rerun()

    # Display final output based on accepted suggestions
    st.divider()
    st.header("Final Output")
    
    if 'original_source' in st.session_state:
        # Diff view
        st.subheader("Change Preview")
        tab1, tab2, tab3 = st.tabs(["Original", "Enhanced", "Diff"])

        final_output = apply_suggestions(st.session_state.original_source)
        edited = st.text_area("Wikipedia-formatted Content", 
                            value=final_output,
                            height=400)
        
        if st.button("Submit Approved Changes"):
            # submission logic here
            st.success("Submitted successfully!")

if __name__ == "__main__":
    st.session_state.processing = False