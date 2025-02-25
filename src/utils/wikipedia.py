import mwclient
import requests
from mwclient import Site
from src.config.settings import config

class WikipediaClient:
    def __init__(self):
        self.site = Site("en.wikipedia.org")
        #self.site.login(config.wiki.user, config.wiki.password)
    
    def get_article_page_source(self, title: str) -> str:
        page = self.site.pages[title]
        return page.text()
    
    # mwclient does not support plaintext so need to use the API 
    def get_article_plain_text(self, title: str) -> str:
        api_url = "https://en.wikipedia.org/w/api.php"

        # Define the parameters
        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'extracts',
            'explaintext': True,
            'exsectionformat': 'plain'
        }

        # Make the request
        response = requests.get(api_url, params=params)
        data = response.json()

        # Extract the plaintext content
        page = next(iter(data['query']['pages'].values()))
        plaintext = page.get('extract', '')
        
        return plaintext
    
    def submit_edit(self, title: str, content: str, summary: str = "WAES-enhanced edit"):
        page = self.site.pages[title]
        page.save(content, summary=summary)
    
    def show_diff(self, original: str, new: str) -> str:
        # Simple diff implementation (replace with difflib for production)
        return f"\n--- Original\n+++ New\n{new[:500]}..."  # Truncated for demo