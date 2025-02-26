from src.agents import ContentAnalyzer, ContentEditor, NeutralityChecker
from src.utils.wikipedia import WikipediaClient
#from utils.file_parser import parse_source_files
from src.config.settings import config
from src.ui.suggestion import Suggestion

def enhance_article(article_title: str, source_paths: list = None) -> list[Suggestion]:
    # Initialize components
    wiki = WikipediaClient()
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
    
    # Process supplemental sources
    supplemental_data = []
    if source_paths:
        print(f"Processing {len(source_paths)} sources...")
        #supplemental_data = parse_source_files(source_paths)


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