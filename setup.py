import os
import re

import setuptools

with open(os.path.join("docker_stack_commands", "__init__.py"), encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setuptools.setup(
    name="docker-stack-commands",
    version=version,
    author="Zeke Marffy",
    author_email="zmarffy@yahoo.com",
    packages=setuptools.find_packages(),
    url='https://github.com/zmarffy/docker-stack-commands',
    license='MIT',
    description='Minimal and limited Python API for dealing with Docker stacks',
    python_requires='>=3.6',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'reequirements',
        'zmtools>=1.4.0'
    ],
)
