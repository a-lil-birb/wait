# helper functions commonly used
import mwparserfromhell
import re

def extract_context_from_words(full_text: str, words: str):
    """Given a full text and a few words, extract the sentence(s) they were in. Splits on periods, so words cannot contain periods."""
    sentence_list = [x for x in full_text.split('.') if any(y in x for y in [words])]
    for sentence in sentence_list:
        sentence = sentence.strip()
    
    return sentence_list

def parse_to_mediawiki(json_data):
    """
    Converts Claude's JSON output to MediaWiki markup with citations
    """
    mediawiki_lines = []
    for content in json_data.get('content', []):
        if content['type'] == 'text':
            text = content['text']
            citations = content.get('citations', [])
            
            if citations:
                citation_refs = []
                for citation in citations:
                    doc_title = citation.get('document_title', 'Unknown Document')
                    start_page = citation.get('start_page_number', '?')
                    end_page = citation.get('end_page_number', start_page)
                    cited_text = citation.get('cited_text', '')
                    
                    # Format page numbers
                    if start_page == end_page:
                        pages = f"page {start_page}"
                    else:
                        pages = f"pages {start_page}–{end_page}"
                    
                    # Create MediaWiki reference
                    ref = f"<ref>{doc_title}, {pages}.</ref>"
                    citation_refs.append(ref)
                
                mediawiki_lines.append(f"{text}{''.join(citation_refs)}")
            else:
                mediawiki_lines.append(text)
    
    return ''.join(mediawiki_lines)

def parse_to_streamlit(json_data):
    """
    Converts Claude's JSON output to a Streamlit-friendly format with numbered citations
    Returns a tuple: (main_text, references)
    """
    main_text_parts = []
    citations_list = []
    
    for content in json_data.get('content', []):
        if content['type'] == 'text':
            text = content['text']
            citations = content.get('citations', [])
            
            if citations:
                citation_indices = []
                for citation in citations:
                    # Add citation to list and record its index
                    citations_list.append(citation)
                    citation_indices.append(len(citations_list))  # 1-based index
                
                # Add citation numbers to text
                citation_marks = ''.join([f'[{i}]' for i in citation_indices])
                main_text_parts.append(f"{text}{citation_marks}")
            else:
                main_text_parts.append(text)
    
    # Format references
    references = []
    for idx, citation in enumerate(citations_list, 1):
        doc_title = citation.get('document_title', 'Unknown Document')
        start_page = citation.get('start_page_number', '?')
        end_page = citation.get('end_page_number', start_page)
        cited_text = citation.get('cited_text', '')
        
        if start_page == end_page:
            pages = f"page {start_page}"
        else:
            pages = f"pages {start_page}–{end_page}"
        
        references.append(
            f"[{idx}] {doc_title}, {pages}. Cited text: \"{cited_text}\""
        )
    
    return (''.join(main_text_parts), references)

def find_excerpt_position(plain_excerpt: str, wikitext: str) -> tuple:
    """
    Find the start and end positions of a plain-text excerpt within wikitext markup.
    
    Args:
        plain_excerpt: Plain text excerpt to find
        wikitext: Full wikitext content
        
    Returns:
        Tuple of (start_index, end_index) or None if not found
    """
    # Normalize input text
    normalized_excerpt = _normalize_text(plain_excerpt)
    
    # Parse wikitext and process nodes
    parsed = mwparserfromhell.parse(wikitext)
    segments = []
    current_pos = 0
    
    for node in parsed.nodes:
        node_text = _process_node(node)
        clean_text = _normalize_text(node_text)
        
        # Track original spans
        start = node.span[0]
        end = node.span[1]
        segments.append({
            'clean': clean_text,
            'start': start,
            'end': end,
            'original': str(node)
        })
    
    # Build search string from cleaned segments
    clean_full = ''.join(seg['clean'] for seg in segments)
    
    # Find position in cleaned text
    pos = clean_full.find(normalized_excerpt)
    if pos == -1:
        return None
    
    # Map position back to original wikitext
    current_len = 0
    start_idx = None
    end_idx = None
    
    for seg in segments:
        seg_len = len(seg['clean'])
        if current_len <= pos < current_len + seg_len:
            start_offset = pos - current_len
            start_idx = seg['start'] + _original_offset(
                seg['original'], seg['clean'], start_offset
            )
        
        if current_len <= pos + len(normalized_excerpt) <= current_len + seg_len:
            end_offset = (pos + len(normalized_excerpt)) - current_len
            end_idx = seg['start'] + _original_offset(
                seg['original'], seg['clean'], end_offset
            )
            break
            
        current_len += seg_len
    
    return (start_idx, end_idx) if start_idx is not None and end_idx is not None else None

def _process_node(node):
    """Extract relevant text from different node types"""
    if isinstance(node, mwparserfromhell.nodes.Text):
        return node.value
    if isinstance(node, mwparserfromhell.nodes.Wikilink):
        return node.text or node.title
    if isinstance(node, mwparserfromhell.nodes.Template):
        return ' '.join([param.value for param in node.params])
    if isinstance(node, mwparserfromhell.nodes.Tag) and node.tag == 'ref':
        return ''
    return ''

def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return re.sub(r'\s+', ' ', text).strip()

def _original_offset(original: str, clean: str, clean_offset: int) -> int:
    """Map offset in cleaned text to original text"""
    clean_counter = 0
    for i, char in enumerate(original):
        if _normalize_text(char) == char:
            clean_counter += 1
        if clean_counter > clean_offset:
            return i
    return len(original)