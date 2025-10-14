"""
Setup configuration for DNB Annales Scraper.

This file allows installation of the package using pip.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
requirements = (this_directory / "requirements.txt").read_text(encoding="utf-8").splitlines()
# Filter out comments and empty lines
requirements = [
    req.strip() for req in requirements 
    if req.strip() and not req.strip().startswith('#')
]

setup(
    name="dnb-annales-scraper",
    version="1.0.0",
    author="Sokratika",
    author_email="contact@sokratika.com",
    description="Un outil Python professionnel pour scraper et télécharger les annales du DNB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/taieb1919/sokratika-ExamScrapper",
    project_urls={
        "Bug Tracker": "https://github.com/taieb1919/sokratika-ExamScrapper/issues",
        "Documentation": "https://github.com/taieb1919/sokratika-ExamScrapper/blob/master/README.md",
        "Source Code": "https://github.com/taieb1919/sokratika-ExamScrapper",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.0.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dnb-scraper=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md"],
    },
    zip_safe=False,
    keywords=[
        "dnb",
        "brevet",
        "annales",
        "scraper",
        "education",
        "france",
        "exam",
        "pdf",
        "download",
        "eduscol",
    ],
)

