from setuptools import find_packages, setup

setup(
    name="py-gol",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "blessed>=1.20",  # Terminal UI
        "typing-extensions>=4.0.0",  # Type hints
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "mypy>=1.9.0",  # Static type checking
        ],
    },
    entry_points={
        "console_scripts": [
            "gol=gol.main:main",
        ],
    },
    # Metadata
    author="Development Team",
    description="Terminal-based Game of Life with actor-based concurrency",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="game-of-life, terminal, actors, concurrent",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
        "Topic :: Games/Entertainment :: Simulation",
    ],
)
