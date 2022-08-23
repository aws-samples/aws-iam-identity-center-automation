from setuptools import find_packages, setup

with open("README.md") as fp:
    long_description = fp.read()

setup(
    name="sso_automation_app",
    version="1.0.0",

    description="A CDK Python app for AWS IAM Identity Center Automation",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "sso_automation_app"},
    packages=find_packages(where="sso_automation_app"),

    install_requires=[
        "aws-cdk-lib>=2.0.0",
    ],

    python_requires=">=3.7.10",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
