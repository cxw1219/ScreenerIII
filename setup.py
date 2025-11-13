"""
ScreenerIII - Real-time Commodity Market Scanner
Setup configuration for package installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements from requirements.txt
requirements = []
requirements_path = this_directory / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read development requirements
dev_requirements = []
dev_requirements_path = this_directory / "requirements-dev.txt"
if dev_requirements_path.exists():
    with open(dev_requirements_path, 'r', encoding='utf-8') as f:
        dev_requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='screener-iii',
    version='1.0.0',

    # Project description
    description='A real-time commodity market scanner with technical analysis and pattern recognition',
    long_description=long_description,
    long_description_content_type='text/markdown',

    # Author information
    author='ScreenerIII Development Team',
    author_email='dev@screener3.com',

    # Project URLs
    url='https://github.com/yourusername/ScreenerIII',
    project_urls={
        'Bug Tracker': 'https://github.com/yourusername/ScreenerIII/issues',
        'Documentation': 'https://github.com/yourusername/ScreenerIII/wiki',
        'Source Code': 'https://github.com/yourusername/ScreenerIII',
    },

    # Package configuration
    packages=find_packages(exclude=['tests', 'tests.*', 'docs']),
    include_package_data=True,
    package_data={
        'screener': ['config/*.json', 'config/*.yaml'],
    },

    # Python version requirement
    python_requires='>=3.9',

    # Dependencies
    install_requires=requirements,

    # Optional dependencies
    extras_require={
        'dev': dev_requirements,
        'test': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.11.1',
            'coverage>=7.3.0',
        ],
        'docs': [
            'sphinx>=7.2.0',
            'sphinx-rtd-theme>=1.3.0',
        ],
    },

    # Entry points for console scripts
    entry_points={
        'console_scripts': [
            'screener=main:main',
            'screener3=main:main',
        ],
    },

    # Package classifiers
    classifiers=[
        # Development status
        'Development Status :: 4 - Beta',

        # Intended audience
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Developers',

        # Topic
        'Topic :: Office/Business :: Financial :: Investment',
        'Topic :: Scientific/Engineering :: Information Analysis',

        # License
        'License :: OSI Approved :: MIT License',

        # Python versions
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',

        # Operating systems
        'Operating System :: OS Independent',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',

        # Environment
        'Environment :: Console',

        # Framework
        'Framework :: AsyncIO',

        # Natural language
        'Natural Language :: English',

        # Additional classifiers
        'Typing :: Typed',
    ],

    # Keywords for PyPI search
    keywords=[
        'trading',
        'commodities',
        'market-scanner',
        'technical-analysis',
        'oanda',
        'real-time',
        'financial-data',
        'forex',
        'stocks',
        'cryptocurrency',
        'pattern-recognition',
        'algorithmic-trading',
        'market-data',
    ],

    # Additional metadata
    platforms=['any'],
    zip_safe=False,

    # License
    license='MIT',
)
