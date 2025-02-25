import argparse
from src.core import enhance_article

def main():
    parser = argparse.ArgumentParser(description="Wikipedia Article Enhancement System")
    parser.add_argument("--article", required=True, help="Wikipedia article title")
    parser.add_argument("--sources", nargs="*", help="Optional source files/URLs")
    args = parser.parse_args()
    
    enhance_article(args.article, args.sources)

if __name__ == "__main__":
    main()