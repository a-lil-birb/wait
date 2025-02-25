from setuptools import setup, find_packages

setup(
    name="waes",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "mwclient>=0.11.0",
        "python-dotenv>=1.0.0",
        "python-magic>=0.4.27",
        "pdfminer.six>=20221105",
        "beautifulsoup4>=4.12.2",
        "spacy>=3.7.4",
        "argparse>=1.4.0",
    ],
    entry_points={
        'console_scripts': [
            'waes = cli:main',
        ],
    },
)