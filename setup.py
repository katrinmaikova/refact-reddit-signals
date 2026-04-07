from setuptools import setup, find_packages

setup(
    name="refact-reddit-signals",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit",
        "praw",
    ],
)
