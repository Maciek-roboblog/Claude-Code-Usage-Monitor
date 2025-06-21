#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    """Read README.md for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Claude Code Usage Monitor - Real-time token usage monitoring for Claude AI"

# Read version from __init__.py or define it here
__version__ = "1.0.0"

setup(
    name="claude-usage-monitor",
    version=__version__,
    author="Maciek",
    author_email="maciek@roboblog.eu",
    description="Real-time terminal monitoring tool for Claude AI token usage",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor",
    project_urls={
        "Bug Reports": "https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues",
        "Source": "https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor",
        "Documentation": "https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/blob/main/README.md",
        "Changelog": "https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases",
    },
    packages=find_packages(),
    py_modules=["ccusage_monitor"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Topic :: Terminals",
        "Topic :: Utilities",
    ],
    keywords=[
        "claude", "ai", "token", "usage", "monitor", "terminal", "real-time",
        "claude-code", "anthropic", "ml", "artificial-intelligence", "cli"
    ],
    python_requires=">=3.6",
    install_requires=[
        "pytz>=2021.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "setuptools>=45.0",
            "wheel>=0.36",
            "twine>=3.0",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-monitor=ccusage_monitor:main",
            "cmonitor=ccusage_monitor:main",
            "ccm=ccusage_monitor:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    license="MIT",
    platforms=["any"],
    
    # Additional metadata
    download_url=f"https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/archive/v{__version__}.tar.gz",
    
    # Package configuration
    package_data={
        "": ["*.md", "*.txt", "*.rst", "LICENSE"],
    },
    
    # Pre-installation checks
    setup_requires=[
        "setuptools>=45.0",
        "wheel>=0.36",
    ],
    
    # Post-installation message
    options={
        "bdist_wheel": {
            "universal": False,  # Not compatible with Python 2
        }
    },
)