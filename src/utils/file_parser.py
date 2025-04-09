# utils/file_parser.py
import requests
import magic
import pdfminer.high_level
from io import BytesIO
from typing import List, Optional
from bs4 import BeautifulSoup
import docx
import markdown
import logging
from pathlib import Path
import re
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentParser:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE = 2048  # For streaming downloads
    
    @classmethod
    def parse_source_urls(cls, urls: List[str]) -> List[str]:
        """Process list of URLs into clean text content"""
        results = []
        for url in urls:
            try:
                content = cls._process_url(url)
                if content:
                    results.append(content)
            except Exception as e:
                logger.error(f"Failed to process {url}: {str(e)}")
        return results

    @classmethod
    def parse_source_files(cls, files: List[bytes]) -> List[str]:
        """Process uploaded files into clean text content"""
        results = []
        for file in files:
            try:
                content = cls._process_file(file)
                if content:
                    results.append(content)
            except Exception as e:
                logger.error(f"Failed to process file: {str(e)}")
        return results
    
    @classmethod
    def parse_uploaded_files(cls, uploaded_files) -> List[str]:
        """Process Streamlit UploadedFile objects"""
        results = []
        for uploaded_file in uploaded_files:
            try:
                file_bytes = uploaded_file.getvalue()
                content = cls._process_file(file_bytes)
                if content:
                    results.append(content)
            except Exception as e:
                logger.error(f"Failed to process {uploaded_file.name}: {str(e)}")
        return results
    
    @classmethod
    def encode_pdfs_into_b64(cls, uploaded_files) -> List[str]:
        """Process Streamlit UploadedFile (preferably pdf) into a b64 string"""
        results = []
        for uploaded_file in uploaded_files:
            try:
                file_bytes = uploaded_file.getvalue()
                b64string = base64.standard_b64encode(file_bytes).decode("utf-8")
                if b64string:
                    results.append(b64string)
            except Exception as e:
                logger.error(f"Failed to process {uploaded_file.name} into a b64 string: {str(e)}")
        return results

    @classmethod
    def _process_url(cls, url: str) -> Optional[str]:
        """Fetch and process content from a URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        # Stream download to handle large files
        with requests.get(url, headers=headers, stream=True) as response:
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            content = b''
            
            if 'text/html' in content_type:
                return cls._parse_html(response.text)
                
            elif 'application/pdf' in content_type:
                for chunk in response.iter_content(cls.CHUNK_SIZE):
                    content += chunk
                    if len(content) > cls.MAX_FILE_SIZE:
                        raise ValueError("PDF file too large")
                return cls._parse_pdf(BytesIO(content))
                
            else:
                logger.warning(f"Unsupported content type {content_type} for URL {url}")
                return None

    @classmethod
    def _process_file(cls, file_bytes: bytes) -> Optional[str]:
        """Process uploaded file bytes"""
        if len(file_bytes) > cls.MAX_FILE_SIZE:
            raise ValueError("File size exceeds limit")
            
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file_bytes)
        buffer = BytesIO(file_bytes)
        
        if file_type == 'application/pdf':
            return cls._parse_pdf(buffer)
        elif file_type == 'text/plain':
            return cls._clean_text(file_bytes.decode('utf-8'))
        elif file_type == 'text/html':
            return cls._parse_html(file_bytes.decode('utf-8'))
        elif file_type == 'text/markdown':
            return cls._parse_markdown(file_bytes.decode('utf-8'))
        elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return cls._parse_docx(buffer)
        else:
            logger.warning(f"Unsupported file type: {file_type}")
            return None

    @staticmethod
    def _parse_html(html: str) -> str:
        """Extract main content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Try to find article content
        article = soup.find('article') or soup.find('div', class_=re.compile('content|main|body', re.I))
        
        text = article.get_text(separator='\n') if article else soup.get_text()
        return ContentParser._clean_text(text)

    @staticmethod
    def _parse_pdf(pdf_stream: BytesIO) -> str:
        """Extract text from PDF"""
        text = pdfminer.high_level.extract_text(pdf_stream)
        return ContentParser._clean_text(text)

    @staticmethod
    def _parse_docx(docx_stream: BytesIO) -> str:
        """Extract text from DOCX"""
        doc = docx.Document(docx_stream)
        return ContentParser._clean_text('\n'.join([p.text for p in doc.paragraphs]))

    @staticmethod
    def _parse_markdown(md_text: str) -> str:
        """Convert markdown to clean text"""
        html = markdown.markdown(md_text)
        return ContentParser._clean_text(BeautifulSoup(html, 'html.parser').get_text())

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove non-printable characters
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        # Truncate to reasonable length for LLM context
        return text.strip() #[:15000]  # Limit to ~15k characters