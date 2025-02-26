from src.agents import ContentAnalyzer, ContentEditor, NeutralityChecker
from src.utils.wikipedia import WikipediaClient
from src.utils.file_parser import ContentParser
from src.config.settings import config
from src.ui.suggestion import Suggestion
from src.ui.logger import StreamlitLogger
import io

def enhance_article(article_title: str, source_files: list[io.BytesIO], source_urls: str) -> list[Suggestion]:
    # Initialize components
    wiki = WikipediaClient()

    parsed_source_files = []
    parsed_source_urls = []
    if len(source_files) > 0:
        StreamlitLogger.log(f"Parsing uploaded files ({len(source_files)})...")
        parsed_source_files :list[str] = ContentParser.parse_uploaded_files(source_files)
    if len(source_urls) > 0:
        StreamlitLogger.log(f"Parsing URLs ({len(source_urls)})...")
        parsed_source_urls :list[str] = ContentParser.parse_source_urls(source_urls)


    StreamlitLogger.log(parsed_source_files)
    StreamlitLogger.log(parsed_source_urls)

    analyzer = ContentAnalyzer()
    #researcher = ResearchAgent()
    editor = ContentEditor()
    neutrality = NeutralityChecker()
    #fact_checker = FactChecker()
    
    suggestion_list :list[Suggestion] = []


    # Fetch article content
    print(f"Analyzing article: {article_title}")
    original_content = wiki.get_article_plain_text(article_title)

    neutral_analysis = neutrality.get_neutral_alternatives(original_content)
    suggestion_list += neutrality.get_suggestions(original_content)
    # Analyze content
    analysis = analyzer.analyze(original_content)


    return suggestion_list
    """
    # Research phase
    research_data = researcher.gather_information(
        article_title,
        analysis["missing_sections"],
        supplemental_data
    )
    
    # Generate edits
    draft_content = editor.generate_improvements(
        original_content,
        analysis,
        research_data
    )
    
    # Fact-check
    verified_content = fact_checker.verify_content(draft_content)
    
    # Show diff and get confirmation
    diff = wiki.show_diff(original_content, verified_content)
    print(f"Proposed changes:\n{diff}")
    
    if input("Accept changes? (y/n): ").lower() == "y":
        wiki.submit_edit(article_title, verified_content)
        print("Edit submitted successfully!")
    
    """