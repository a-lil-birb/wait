# helper functions commonly used

def extract_context_from_words(full_text: str, words: str):
    """Given a full text and a few words, extract the sentence(s) they were in. Splits on periods, so words cannot contain periods."""
    sentence_list = [x for x in full_text.split('.') if any(y in x for y in [words])]
    for sentence in sentence_list:
        sentence = sentence.strip()
    
    return sentence_list