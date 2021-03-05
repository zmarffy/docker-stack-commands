from reequirements import Requirement

from .api import *

__version__ = "1.0.0"


REQUIREMENTS = [
    Requirement("docker", ["docker", "-v"]),
]
for requirement in REQUIREMENTS:
    requirement.check()
