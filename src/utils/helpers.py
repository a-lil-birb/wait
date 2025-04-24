# helper functions commonly used
import mwparserfromhell
import html
from mwparserfromhell.nodes import Tag, Template, Wikilink, Text
import re
from typing import Optional, Tuple, List, Dict
import urllib.parse

def extract_context_from_words(full_text: str, words: str):
    """Given a full text and a few words, extract the sentence(s) they were in. Splits on periods, so words cannot contain periods."""
    sentence_list = [x for x in full_text.split('.') if any(y in x for y in [words])]
    for sentence in sentence_list:
        sentence = sentence.strip()
    
    return sentence_list

def parse_to_mediawiki(message):
    """
    Converts Claude's JSON output to MediaWiki markup with citations
    """
    mediawiki_lines = []
    for content in message.content:
        if content.type == 'text':
            text = content.text
            citations = content.citations
            
            if citations:
                citation_refs = []
                for citation in citations:
                    doc_title = citation.document_title
                    start_page = citation.start_page_number
                    end_page = citation.end_page_number
                    cited_text = citation.cited_text
                    
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

def parse_to_streamlit(message):
    """
    Converts Claude's JSON output to a Streamlit-friendly format with numbered citations
    Returns a tuple: (main_text, references)
    """
    main_text_parts = []
    citations_list = []
    
    for content in message.content:
        if content.type == 'text':
            text = content.text
            citations = content.citations
            
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
        doc_title = citation.document_title
        start_page = citation.start_page_number
        end_page = citation.end_page_number
        cited_text = citation.cited_text
        
        if start_page == end_page:
            pages = f"page {start_page}"
        else:
            pages = f"pages {start_page}–{end_page}"
        
        references.append(
            f"[{idx}] {doc_title}, {pages}. Cited text: \"{cited_text}\""
        )
    
    return (''.join(main_text_parts), references)


def find_excerpt_position(plain_excerpt: str, wikitext: str) -> Optional[Tuple[int, int]]:
    """
    Find the position of a plain text excerpt within wikitext.
    
    Args:
        plain_excerpt: The plain text excerpt to find
        wikitext: The wikitext source to search in
        
    Returns:
        A tuple of (start_index, end_index) in the wikitext, or None if not found
    """
    # Parse the wikitext
    wikicode = mwparserfromhell.parse(wikitext)
    
    # Get the plain text version of the wikitext
    plain_text = wikicode.strip_code()
    
    # Create a clean version of both texts for matching
    clean_plain_excerpt = re.sub(r'\s+', ' ', plain_excerpt).strip()
    clean_plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    
    # First try exact matching
    excerpt_pos = clean_plain_text.find(clean_plain_excerpt)
    
    if excerpt_pos == -1:
        # If exact match fails, try more flexible matching
        return fuzzy_find_excerpt(clean_plain_excerpt, wikitext)
    
    # Build the mapping between plain text and wikitext
    mapping = build_text_to_wikitext_mapping(wikicode, wikitext)
    
    # Find the actual starting position in clean_plain_text
    actual_start_pos = 0
    for i in range(len(clean_plain_text)):
        if i == excerpt_pos:
            actual_start_pos = mapping[i]["wikitext_pos"] if i < len(mapping) else 0
            break
    
    # Get the approximate end of the excerpt in wikitext
    # We'll refine this by checking the rendered text
    approx_wiki_len = len(clean_plain_excerpt) * 3  # Estimate wikitext is 3x longer than plain text
    
    # Start from a potential end position and gradually reduce until we match
    for end_pos in range(actual_start_pos + approx_wiki_len, actual_start_pos, -1):
        if end_pos >= len(wikitext):
            end_pos = len(wikitext) - 1
            
        candidate_wikitext = wikitext[actual_start_pos:end_pos]
        candidate_plain = mwparserfromhell.parse(candidate_wikitext).strip_code()
        candidate_plain = re.sub(r'\s+', ' ', candidate_plain).strip()
        
        # Check if this candidate contains our excerpt
        if clean_plain_excerpt in candidate_plain:
            # Now find the minimum wikitext that contains the excerpt
            for i in range(end_pos, actual_start_pos, -1):
                shorter_wikitext = wikitext[actual_start_pos:i]
                shorter_plain = mwparserfromhell.parse(shorter_wikitext).strip_code()
                shorter_plain = re.sub(r'\s+', ' ', shorter_plain).strip()
                
                if clean_plain_excerpt not in shorter_plain:
                    return actual_start_pos, i
            
            return actual_start_pos, end_pos
    
    # If we couldn't find a good match with the mapping approach, try the fallback
    return fallback_find_excerpt(plain_excerpt, wikitext)

def build_text_to_wikitext_mapping(wikicode, wikitext):
    """Build a mapping from positions in plain text to positions in wikitext."""
    mapping = []
    current_wikitext_pos = 0
    
    for node in wikicode.nodes:
        if isinstance(node, mwparserfromhell.nodes.text.Text):
            # For plain text nodes, each character maps directly
            for char in str(node):
                mapping.append({
                    "char": char,
                    "wikitext_pos": current_wikitext_pos
                })
                current_wikitext_pos += 1
        else:
            # For complex nodes (templates, links, etc.)
            node_wikitext = str(node)
            node_plain = node.strip_code() if hasattr(node, 'strip_code') else ''
            
            # Map each plain text character to the start of this node
            for char in node_plain:
                mapping.append({
                    "char": char,
                    "wikitext_pos": current_wikitext_pos
                })
            
            # Update wikitext position to end of this node
            current_wikitext_pos += len(node_wikitext)
    
    return mapping

def fuzzy_find_excerpt(plain_excerpt, wikitext):
    """Use a more flexible approach to find the excerpt by checking multiple windows."""
    clean_excerpt = re.sub(r'\s+', ' ', plain_excerpt).strip()
    words = clean_excerpt.split()
    
    # Look for the start and end words
    start_word = words[0]
    end_word = words[-1]
    
    # Find potential start positions
    start_positions = []
    for match in re.finditer(re.escape(start_word), wikitext):
        start_positions.append(match.start())
    
    # Find potential end positions
    end_positions = []
    for match in re.finditer(re.escape(end_word), wikitext):
        end_positions.append(match.end())
    
    # Try various start and end combinations
    for start in start_positions:
        for end in end_positions:
            if end <= start:
                continue
                
            # Only consider reasonable lengths to avoid checking the entire document
            if end - start > len(plain_excerpt) * 5:
                continue
                
            candidate = wikitext[start:end]
            candidate_plain = mwparserfromhell.parse(candidate).strip_code()
            candidate_plain = re.sub(r'\s+', ' ', candidate_plain).strip()
            
            # Check if the excerpt is contained in this candidate
            if clean_excerpt in candidate_plain:
                return start, end
    
    return fallback_find_excerpt(plain_excerpt, wikitext)

def fallback_find_excerpt(plain_excerpt, wikitext):
    """Last resort approach for complex cases."""
    # Generate overlapping chunks of the wikitext
    chunk_size = min(len(wikitext), 1000)  # Use reasonably sized chunks
    overlap = 200
    
    for i in range(0, len(wikitext), chunk_size - overlap):
        chunk = wikitext[i:i+chunk_size]
        chunk_plain = mwparserfromhell.parse(chunk).strip_code()
        chunk_plain = re.sub(r'\s+', ' ', chunk_plain).strip()
        
        clean_excerpt = re.sub(r'\s+', ' ', plain_excerpt).strip()
        
        if clean_excerpt in chunk_plain:
            # Found the chunk, now narrow down
            for start in range(i, i+chunk_size):
                for end in range(start + len(clean_excerpt), i+chunk_size + 1):
                    # Don't check sections that are too large
                    if end - start > len(clean_excerpt) * 5:
                        continue
                        
                    section = wikitext[start:end]
                    section_plain = mwparserfromhell.parse(section).strip_code()
                    section_plain = re.sub(r'\s+', ' ', section_plain).strip()
                    
                    if clean_excerpt in section_plain:
                        # Try to find the minimum section that contains the excerpt
                        minimum_length = end - start
                        best_start, best_end = start, end
                        
                        for s in range(start, end):
                            for e in range(s + len(clean_excerpt), end + 1):
                                subsection = wikitext[s:e]
                                subsection_plain = mwparserfromhell.parse(subsection).strip_code()
                                subsection_plain = re.sub(r'\s+', ' ', subsection_plain).strip()
                                
                                if clean_excerpt in subsection_plain and e - s < minimum_length:
                                    minimum_length = e - s
                                    best_start, best_end = s, e
                        
                        return best_start, best_end
    
    return None

def process_node(node):
    """Recursively process nodes with explicit tag handling"""
    if isinstance(node, Text):
        return html.unescape(node.value)
    
    if isinstance(node, Wikilink):
        return node.title.strip_code().strip()
    
    if isinstance(node, Template):
        return ""  # Remove templates
    
    if isinstance(node, Tag):
        if node.tag == "table":
            return process_table(node)
        # Process other tags' contents (like <ref>, <br>) but remove the tags themselves
        return "".join(process_node(n) for n in node.contents.nodes)
    
    # Fallback for other node types
    try:
        return html.unescape(node.strip_code().strip())
    except AttributeError:
        return str(node) if node else ""

def process_table(table_node):
    """Convert wikitable to plain text with proper formatting"""
    table_text = []
    
    for row in table_node.contents.filter_tags(matches=lambda n: n.tag == "tr"):
        cells = []
        for cell in row.contents.filter_tags(matches=lambda n: n.tag in ["td", "th"]):
            cell_content = "".join(process_node(n) for n in cell.contents.nodes)
            cells.append(cell_content.strip())
        
        if cells:  # Skip empty rows
            table_text.append(" | ".join(cells))
    
    return "\n".join(table_text)

def wikitext_to_plaintext(wikitext):
    parsed = mwparserfromhell.parse(wikitext)
    processed = []
    
    for node in parsed.nodes:
        processed.append(process_node(node))
    
    # Combine and clean up while preserving paragraphs
    return "\n".join(
        line.strip() for line in "".join(processed).splitlines() 
        if line.strip()
    )

def process_node_skip_special(node):
    """Process nodes while skipping tables and references entirely"""
    if isinstance(node, Text):
        return html.unescape(node.value)
    
    if isinstance(node, Wikilink):
        return node.title.strip_code().strip()
    
    if isinstance(node, Template):
        return ""  # Remove templates
    
    if isinstance(node, Tag):
        # Skip tables and references completely
        if node.tag in ["table", "ref"]:
            return ""
        # Process other tags' contents
        return "".join(process_node_skip_special(n) for n in node.contents.nodes)
    
    # Fallback for other node types
    try:
        return html.unescape(node.strip_code().strip())
    except AttributeError:
        return str(node) if node else ""

def wikitext_to_plaintext_skip_tables_refs(wikitext):
    parsed = mwparserfromhell.parse(wikitext)
    processed = []
    
    for node in parsed.nodes:
        processed.append(process_node_skip_special(node))
    
    # Combine results while preserving paragraph breaks
    return "\n\n".join(
        "\n".join(line.strip() for line in part.splitlines() if line.strip())
        for part in "".join(processed).split("\n\n")
        if part.strip()
    )

def strip_code_block(text):
    # Pattern to match:
    # 1. Optional whitespace + ``` + optional whitespace + optional "json" + optional whitespace
    # 2. Capture the content inside
    # 3. Optional whitespace + ``` + optional whitespace
    pattern = r'^\s*```\s*(?:json\s*)?(.*?)\s*```\s*$'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

def get_wikipedia_link(title):
    # Handle empty input
    if not title.strip():
        return ""
    
    # Replace spaces with underscores and capitalize the first letter
    processed_title = title.strip().replace(' ', '_')
    if processed_title:
        processed_title = processed_title[0].upper() + processed_title[1:]
    
    # URL-encode special characters while preserving underscores
    encoded_title = urllib.parse.quote(processed_title, safe='_')
    
    return f"https://en.wikipedia.org/wiki/{encoded_title}"