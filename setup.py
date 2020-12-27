import setuptools
import zetuptools
from reequirements import Requirement

REQUIREMENTS = [
    Requirement("docker", ["docker", "-v"]),
]
for requirement in REQUIREMENTS:
    requirement.check()

TOOLS = zetuptools.SetuptoolsExtensions(
    "docker-stack-commands", "Zeke Marffy", "zmarffy@yahoo.com")


setuptools.setup(
    name=TOOLS.name,
    version=TOOLS.version,
    author=TOOLS.author,
    author_email=TOOLS.author_email,
    packages=setuptools.find_packages(),
    url='https://github.com/zmarffy/docker-stack-commands',
    license='MIT',
    description='Minimal and limited Python API for dealing with Docker stacks',
    python_requires=TOOLS.minimum_version_required,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'reequirements',
        'zmtools>=1.4.0',
        'zetuptools>=2.3.0'
    ],
)
