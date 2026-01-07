from setuptools import setup, find_packages

setup(
    name="rahkaran-client",
    version="0.1.0",
    description="A Python client for interacting with Rahkaran ERP APIs.",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        # Note: rahkaran_login_webservice is a git dependency. All dependencies are in requirements.txt.
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
