from setuptools import setup, find_packages

setup(
    name="parabula",
    version="0.1.0",
    description="Sistema de análise de interações entre medicamentos",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "openrouter",
    ],
)
