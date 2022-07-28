import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pytest-playwright",
    author="Microsoft",
    author_email="",
    description="A pytest wrapper with fixtures for Playwright to automate web browsers",
    license="Apache License 2.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/microsoft/playwright-pytest",
    packages=["pytest_playwright"],
    include_package_data=True,
    install_requires=[
        "playwright>=1.18",
        "pytest>=6.2.4,<8.0.0",
        "pytest-base-url>=1.0.0,<3.0.0",
        "python-slugify>=6.0.0,<7.0.0",
    ],
    entry_points={"pytest11": ["playwright = pytest_playwright.pytest_playwright"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Framework :: Pytest",
    ],
    python_requires=">=3.7",
    use_scm_version={
        "version_scheme": "post-release",
        "write_to": "pytest_playwright/_repo_version.py",
        "write_to_template": 'version = "{version}"\n',
    },
    setup_requires=["setuptools_scm"],
)
