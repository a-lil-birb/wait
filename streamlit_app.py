import streamlit as st
import streamlit.components.v1 as components
from src.core import enhance_article
from src.utils.wikipedia import WikipediaClient
from src.ui.logger import StreamlitLogger
#from utils.file_parser import parse_source_files
import time

# Initialize logger with Streamlit callback
def setup_logger():
    def streamlit_log(message: str):
        if 'log' not in st.session_state:
            st.session_state.log = []
        st.session_state.log.append(f"{time.strftime('%H:%M:%S')} - {message}")
        if len(st.session_state.log) > 100:  # Keep last 100 messages
            st.session_state.log.pop(0)
    
    StreamlitLogger.initialize(streamlit_log)

setup_logger()

# Initialize Wikipedia Client
wiki = WikipediaClient()
st.set_page_config(page_title="WAIT Editor", layout="wide")

# Session state initialization
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'log' not in st.session_state:
    st.session_state.log = []

# Sidebar for inputs
with st.sidebar:
    st.header("Article Input")
    article_title = st.text_input("Wikipedia Article Title", "Machine learning")
    sources = st.file_uploader("Upload Source Documents", 
                              type=["pdf", "txt", "md", "html"],
                              accept_multiple_files=True)
    urls = st.text_input("Source URLs (comma-separated)", "")

def show_processing_log():
    st.markdown("""
    <style>
    .log-container {
        height: 500px;
        overflow-y: auto;
        background-color: #0E1117;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .log-entry {
        font-family: monospace;
        white-space: pre-wrap;
        margin: 5px 0;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.subheader("🔄 Processing Log")
        log_container = st.empty()
        
        # Show log entries with wrapping
        with log_container.container():
            components.html(
                f"""
                <div class="log-container">
                    {"".join([
                        f'<div class="log-entry">{entry}</div>' 
                        for entry in st.session_state.log[-100:]
                    ])}
                </div>
                <script>
                    // Auto-scroll to bottom
                    window.onload = function() {{
                        var logDiv = document.querySelector('.log-container');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }};
                </script>
                """,
                height=520  # Match container height + padding
            )

# Add test messages
if st.button("Add Test Message"):
    st.session_state.log.append("This is a long test message that should wrap automatically. " * 5)



# Main interface
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Article Analysis")
    
    if st.button("Analyze and Enhance") and not st.session_state.processing:
        st.session_state.processing = True
        
        with st.status("Processing...", expanded=True) as status:
            try:
                # Get article content
                StreamlitLogger.log("Fetching Wikipedia article...")
                original_content = wiki.get_article_plain_text(article_title)
                
                # Process sources
                source_data = []
                if sources:
                    StreamlitLogger.log("Parsing uploaded files...")
                    #source_data += parse_source_files(sources)
                
                if urls:
                    StreamlitLogger.log("Processing URLs...")
                    # Add URL processing logic here
                
                # Run enhancement pipeline
                StreamlitLogger.log("Starting enhancement process...")
                enhanced_content = enhance_article(article_title, source_data)
                
                # Store results
                st.session_state.original = original_content
                st.session_state.enhanced = enhanced_content
                status.update(label="Processing complete!", state="complete")
                
            except Exception as e:
                StreamlitLogger.log(f"Error: {str(e)}")
                status.update(label="Error occurred", state="error")
            finally:
                st.session_state.processing = False

    # Real-time log display
    st.subheader("Processing Log")
    """
    log_container = st.container(height=300)
    with log_container:
        for message in st.session_state.log[-20:]:  # Show last 20 messages
            st.code(message, language="text")
    """
    show_processing_log()
    

with col2:
    if 'enhanced' in st.session_state:
        st.header("Suggested Improvements")
        
        # Improvement suggestions
        with st.expander("📑 Missing Citations (3)"):
            st.markdown("""
            - Claim about neural networks needs citation
            - 2023 performance metrics unsourced
            - Historical context requires reference
            """)
        
        with st.expander("📈 Readability Issues"):
            st.markdown("""
            - Flesch-Kincaid Grade Level: 15.2 (aim for <12)
            - Long paragraphs detected in Introduction section
            """)
        
        with st.expander("🔍 Missing Sections"):
            st.markdown("""
            - Recommended sections to add:
              * Ethical Considerations
              * Recent Developments (2023-2024)
            """)
        
        st.divider()
        st.header("Final Output")
        
        # Diff view
        st.subheader("Change Preview")
        st.tabs(["Original", "Enhanced", "Diff"])
        
        # Editable output
        st.subheader("WikiText Output")
        edited_content = st.text_area("Edit before submission:", 
                                    value=st.session_state.enhanced,
                                    height=400)
        
        if st.button("Submit to Wikipedia"):
            wiki.submit_edit(article_title, edited_content)
            st.success("Edit submitted successfully!")