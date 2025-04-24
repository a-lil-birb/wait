from src.agents import ContentAnalyzer, ContentEditor, ResearcherAgent, NeutralityChecker, ResearcherAgentV2, LinkingImprover
from src.utils.wikipedia import WikipediaClient
from src.utils.file_parser import ContentParser
from src.config.settings import config
from src.ui.suggestion import Suggestion
from src.ui.logger import StreamlitLogger
import io

def _research_text(article_title: str, parsed_source_list: list[str], source_source: str) -> tuple[list[ResearcherAgent],list[str]]:
    researcher_upload_list : list[ResearcherAgent] = []
    researcher_upload_output_list :list[str] = []
    
    for idx, parsed_source in enumerate(parsed_source_list, start=1):
        new_researcher = ResearcherAgent(article_title, parsed_source)
        StreamlitLogger.log(f"Researching {source_source} source {idx}...")
        researcher_output = new_researcher.summarize_source()

        researcher_upload_list.append(new_researcher)
        researcher_upload_output_list.append(researcher_output)
        StreamlitLogger.log(f"[ResearcherAgent#{idx}-{source_source}] Response:\n{researcher_output}")

    return researcher_upload_list,researcher_upload_output_list

def _research_text_v2(article_title: str, b64source_strs: list[str], source_source: str):
    researcher_upload_list : list[ResearcherAgentV2] = []
    researcher_upload_output_list :list[str] = []
    
    for idx, parsed_source in enumerate(b64source_strs, start=1):
        new_researcher = ResearcherAgentV2(article_title, parsed_source)
        StreamlitLogger.log(f"Researching {source_source} source {idx}...")
        researcher_output = new_researcher.summarize_source()

        researcher_upload_list.append(new_researcher)
        researcher_upload_output_list.append(researcher_output)
        StreamlitLogger.log(f"[ResearcherAgentV2#{idx}-{source_source}] Response:\n{researcher_output}")

    return researcher_upload_list,researcher_upload_output_list


def _analyze_research_and_article(article_title: str, article_content: str, summary: str):
    new_analyzer = ContentAnalyzer(article_title, article_content, summary)
    analysis = new_analyzer.find_missing_information()
    return analysis

def _edit_article(article_title: str, article_content: str, summary: str, idx: int) -> list[Suggestion]:
    new_editor = ContentEditor(article_title, article_content, summary, idx)
    new_editor.improve_article_with_missing_info()
    return new_editor.get_diff_suggestions()

def enhance_article(article_title: str, source_files: list[io.BytesIO], source_urls: str) -> list[Suggestion]:
    # Initialize components
    wiki = WikipediaClient()

    parsed_source_files = []
    parsed_source_urls = []
    b64_encoded_sources = []
    if len(source_files) > 0:
        StreamlitLogger.log(f"Parsing uploaded files ({len(source_files)})...")
        #parsed_source_files :list[str] = ContentParser.parse_uploaded_files(source_files)
        b64_encoded_sources :list[str] = ContentParser.encode_pdfs_into_b64(source_files)
    if len(source_urls) > 0:
        StreamlitLogger.log(f"Parsing URLs ({len(source_urls)})...")
        #parsed_source_urls :list[str] = ContentParser.parse_source_urls(source_urls)

    # Research the provided sources
    researcher_upload_list : list[ResearcherAgent] = []
    researcher_upload_output_list :list[str] = []
    researcher_upload_list, researcher_upload_output_list = _research_text(article_title, parsed_source_files, "uploaded")
    
    researcher_url_list : list[ResearcherAgent] = []
    researcher_url_output_list :list[str] = []
    researcher_url_list, researcher_url_output_list = _research_text(article_title, parsed_source_urls, "URL")

    #analyzer = ContentAnalyzer()
    #researcher = ResearchAgent()
    #editor = ContentEditor()
    neutrality = NeutralityChecker()
    #fact_checker = FactChecker()
    
    suggestion_list :list[Suggestion] = []

    # Fetch article content
    print(f"Analyzing article: {article_title}")
    original_content = wiki.get_article_plain_text(article_title)

    #StreamlitLogger.log(f"{len(researcher_upload_output_list+researcher_url_output_list)}")
    for idx, research in enumerate(researcher_upload_output_list+researcher_url_output_list, start=1):
        analysis = _analyze_research_and_article(article_title, original_content, research)
        StreamlitLogger.log(f"[Analyzer#{idx}] Response:\n{analysis}")
        edit_suggestions = _edit_article(article_title, original_content, analysis, idx)
        StreamlitLogger.log(f"[ContentEditor#{idx}] Edit Diff List:\n{edit_suggestions}")
        
        suggestion_list += edit_suggestions
    
    neutrality.get_neutral_alternatives(original_content)
    suggestion_list += neutrality.get_suggestions(original_content)


    # ResearcherV2

    return suggestion_list

def check_neutrality(article_title: str, article_content: str, wikitext_content):
    suggestion_list :list[Suggestion] = []

    neutrality = NeutralityChecker()

    neutrality.get_neutral_alternatives(article_content)
    suggestion_list += neutrality.get_suggestions(article_content)

    return suggestion_list

def improve_linking(article_title: str, article_content: str, wikitext_content):
    suggestion_list :list[Suggestion] = []

    link_improver = LinkingImprover(article_title, wikitext_content)

    link_improver.execute_flow()
    suggestion_list += link_improver.get_suggestions()

    return suggestion_list

def summarize_sources(article_title: str, article_content: str, wikitext_content, sources):
    b64_file_list = ContentParser.encode_pdfs_into_b64(sources)
    StreamlitLogger.log("Encoded sources.")
    summaries = []

    for i in range(len(b64_file_list)):
        StreamlitLogger.log(f"Parsing source ({i+1})")
        researcherV2 = ResearcherAgentV2(article_title, b64_file_list[i], article_content)

        researcherV2.summarize_source()
        summaries.append(researcherV2.stparsed_response)

    return summaries 

def enhance_with_source_summaries(article_title: str, article_content: str, wikitext_content, summaries):
    suggestion_list :list[Suggestion] = []

    StreamlitLogger.log("Generating suggestions...")
    for idx, summary in enumerate(summaries, start=1):
        parsed_summary = f"{summary[0]}\n\n{'\n'.join(summary[1])}"

        analysis = _analyze_research_and_article(article_title, article_content, parsed_summary)
        StreamlitLogger.log(f"[Analyzer#{idx}] Response:\n{analysis}")
        edit_suggestions = _edit_article(article_title, article_content, analysis, idx)
        StreamlitLogger.log(f"[ContentEditor#{idx}] Edit Diff List:\n{edit_suggestions}")
        
        suggestion_list += edit_suggestions

    return suggestion_list