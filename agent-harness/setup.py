from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-uuk-timeline",
    version="1.0.0",
    description="CLI harness for uuk-timeline — Prophetic Timeline web application",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0",
    ],
    package_data={
        "cli_anything.uuk_timeline": ["skills/*.md"],
    },
    entry_points={
        "console_scripts": [
            "uuk-timeline=cli_anything.uuk_timeline.uuk_timeline_cli:main",
        ],
    },
    python_requires=">=3.8",
)
