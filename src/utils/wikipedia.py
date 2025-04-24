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
    
    # to create links
    def exists_article(self, title: str, excerpt_length=200):
        """
        Check if a Wikipedia article exists and return an excerpt of its introduction.
        
        Args:
            title (str): Title of the Wikipedia article to check
            excerpt_length (int): Maximum length of the excerpt to return (default: 200)
        
        Returns:
            dict: A dictionary containing:
                - 'exists': boolean indicating if article exists
                - 'excerpt': string with excerpt (empty if article doesn't exist)
                - 'url': string with full URL to article (empty if article doesn't exist)
        """
        result = {
            'exists': False,
            'excerpt': '',
            'url': ''
        }
        
        try:
            # Connect to Wikipedia
            site = self.site
            
            # Get the page
            page = site.pages[title]
            
            if page.exists:
                result['exists'] = True
                result['url'] = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                
                # Get the page text
                text = self.get_article_plain_text(title)
                result['excerpt'] = text[:excerpt_length]
        
        except Exception as e:
            print(f"Error accessing Wikipedia: {e}")
        
        return result

    
    def show_diff(self, original: str, new: str) -> str:
        # Simple diff implementation (replace with difflib for production)
        return f"\n--- Original\n+++ New\n{new[:500]}..."  # Truncated for demo