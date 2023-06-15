from setuptools import setup

with open("requirements.txt", "r", encoding="UTF-8") as f:
    required = f.read().splitlines()

setup(
    name="elfpy",
    install_requires=required,
)
