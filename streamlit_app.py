import streamlit as st
import streamlit.components.v1 as components
from src.core import enhance_article
from src.utils.wikipedia import WikipediaClient
from src.ui.logger import StreamlitLogger
from src.ui.suggestion import Suggestion
import time
import random

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

    st.subheader("Processing Log")
    with st.container(height=400):
        
        log_container = st.empty()
        
        # Show log entries with wrapping
        with log_container.container():
            for message in st.session_state.log: #[-20:]:  # Show last 20 messages
                st.code(message, language="text", wrap_lines=True)

# Initialize logger with Streamlit callback
def setup_logger():
    def streamlit_log(message: str):
        if 'log' not in st.session_state:
            st.session_state.log = []
        st.session_state.log.append(f"{time.strftime('%H:%M:%S')} - {message}")
        if len(st.session_state.log) > 100:  # Keep last 100 messages
            st.session_state.log.pop(0)
        show_processing_log()
    
    StreamlitLogger.initialize(streamlit_log)

setup_logger()

# Main interface
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Article Analysis")
    
    if st.button("Analyze and Improve") and not st.session_state.processing:
        st.session_state.processing = True
        
        with st.status("Processing...", expanded=True) as status:
            try:
                # Get article content
                StreamlitLogger.log("Fetching Wikipedia article...")
                original_content = wiki.get_article_plain_text(article_title)
                original_wikitext_content = wiki.get_article_page_source(article_title)
                
                # Process sources
                #source_file_data = []
                source_url_data = []
                if sources:
                    pass
                
                if urls:
                    split_urls = urls.split(",")
                    for url in split_urls:
                        url.strip()
                    source_url_data = split_urls
                
                # Run enhancement pipeline
                StreamlitLogger.log("Starting improvement process...")
                enhancement_suggestions :list[Suggestion] = enhance_article(article_title, sources, source_url_data)
                
                # Store results
                st.session_state.original = original_content
                st.session_state.original_source = original_wikitext_content
                #st.session_state.enhanced = enhanced_content

                st.session_state.suggestion_list = enhancement_suggestions
                
                status.update(label="Processing complete!", state="complete")
                
            except Exception as e:
                StreamlitLogger.log(f"Error: {str(e)}")
                status.update(label="Error occurred", state="error")
            finally:
                st.session_state.processing = False
                
                #StreamlitLogger.log(enhancement_suggetions)
    
    show_processing_log()

## suggestions

# Initialize session state for suggestions
if 'suggestion_list' not in st.session_state:
    st.session_state.suggestion_list = []



# Function to apply accepted suggestions
def apply_suggestions(original: str) -> str:
    pass
    return original

# Display suggestions with approval buttons
if st.session_state.suggestion_list:
    st.header("Improvement Suggestions")
    
    for idx, suggestion in enumerate(st.session_state.suggestion_list):
        suggestion :Suggestion
        with st.expander(f"Suggestion #{idx+1}: {suggestion.type}", expanded=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                **{suggestion.text}**  
                <em>Context: {suggestion.context}</em>
                """, unsafe_allow_html=True)
                
            with col2:
                if suggestion.status == 'accepted':
                    st.success("✅ Accepted")
                    if st.button("Revoke", key=f"revoke_{idx}"):
                        st.session_state.suggestion_list[idx].status = 'pending'
                elif suggestion.status == 'rejected':
                    st.error("❌ Rejected")
                    if st.button("Reconsider", key=f"reconsider_{idx}"):
                        st.session_state.suggestion_list[idx].status = 'pending'
                else:
                    if st.button("Accept", key=f"accept_{idx}"):
                        st.session_state.suggestion_list[idx].status = 'accepted'
                    if st.button("Reject", key=f"reject_{idx}"):
                        st.session_state.suggestion_list[idx].status = 'rejected'

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


# with col2:
#     if 'enhanced' in st.session_state:
#         st.header("Suggested Improvements")
        
#         # Improvement suggestions
#         with st.expander("📑 Missing Citations (3)"):
#             st.markdown("""
#             - Claim about neural networks needs citation
#             - 2023 performance metrics unsourced
#             - Historical context requires reference
#             """)
        
#         with st.expander("📈 Readability Issues"):
#             st.markdown("""
#             - Flesch-Kincaid Grade Level: 15.2 (aim for <12)
#             - Long paragraphs detected in Introduction section
#             """)
        
#         with st.expander("🔍 Missing Sections"):
#             st.markdown("""
#             - Recommended sections to add:
#               * Ethical Considerations
#               * Recent Developments (2023-2024)
#             """)
        
#         st.divider()
#         st.header("Final Output")
        
#         # Diff view
#         st.subheader("Change Preview")
#         tab1, tab2, tab3 = st.tabs(["Original", "Enhanced", "Diff"])
        
#         # Editable output
#         st.subheader("WikiText Output")
#         edited_content = st.text_area("Edit before submission:", 
#                                     value=st.session_state.enhanced,
#                                     height=400)
        
#         if st.button("Submit to Wikipedia"):
#             wiki.submit_edit(article_title, edited_content)
#             st.success("Edit submitted successfully!")