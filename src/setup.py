from setuptools import setup, find_packages

setup(
    name="wait",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "anthropic==0.49.0",
        "openai>=1.0.0",
        "mwclient>=0.11.0",
        "mwparserfromhell==0.6.6",
        "Markdown==3.7"
        "python-dotenv>=1.0.0",
        "python-magic>=0.4.27",
        "pdfminer.six>=20221105",
        "beautifulsoup4>=4.12.2",
        "spacy>=3.7.4",
        "argparse>=1.4.0",
    ],
    entry_points={
        'console_scripts': [
            'wait = cli:main',
        ],
    },
)