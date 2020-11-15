import itertools
import re
import subprocess
import time
import uuid

import yaml
from zmtools import loading_animation


def _command_loop(cmd, args, expected, max_attempts=2, pause=2, negative=False):
    attempt_num = 0
    out = None
    while attempt_num <= max_attempts:
        attempt_num += 1
        succeeded = True
        out = subprocess.check_output(
            [cmd] + args, stderr=subprocess.STDOUT).decode().strip()
        if not isinstance(expected, list):
            expected = [expected]
        for e in expected:
            if isinstance(e, re.Pattern):
                if not negative:
                    if not re.findall(e, out):
                        succeeded = False
                        break
                else:
                    if re.findall(e, out):
                        succeeded = False
                        break
            else:
                if not negative:
                    if not e in out:
                        succeeded = False
                        break
                else:
                    if e in out:
                        succeeded = False
                        break
        if succeeded:
            return True, out
        else:
            time.sleep(pause)
    return False, out


class Stack():
    def __init__(self, stack_yaml_file_locations, stack_name=None, components_mapping={}):
        if stack_name is None:
            stack_name = str(uuid.uuid4()).replace("-", "")
        self.stack_name = stack_name
        self.stack_yaml_file_locations = stack_yaml_file_locations
        components = []
        for stack_yaml_file_location in self.stack_yaml_file_locations:
            with open(stack_yaml_file_location, "r") as f:
                components.extend(
                    list(yaml.load(f, Loader=yaml.FullLoader)["services"].keys()))
        self.components = components
        self.components_mapping = components_mapping
        self._status_args = ["service", "logs", "--raw"]

    @property
    def _teardown_args(self):
        return ["stack", "rm", self.stack_name]

    @property
    def _check_deployed_args(self):
        return ["ps", "--filter", f"name={self.stack_name}", "--format", "'{{ .Names }}'"]

    @property
    def _deployed_validation(self):
        return [f"{self.stack_name}_{component}" for component in self.components]

    @property
    def _deploying_validation(self):
        return [f"Creating service {self.stack_name}_{component}" for component in self.components]

    @property
    def _tearing_down_validation(self):
        return [f"Removing service {self.stack_name}_{component}" for component in self.components]

    @property
    def _deploy_args(self):
        return ["stack", "deploy", self.stack_name] + list(itertools.chain.from_iterable([["-c", stack_yaml_file_location] for stack_yaml_file_location in self.stack_yaml_file_locations]))

    def check_deployed(self, should_be_deployed=False, quick_check=False):
        if should_be_deployed:
            negative = False
            if not quick_check:
                max_attempts = 2
                pause = 3
            else:
                max_attempts = 1
                pause = 0
            phrase = "Checking deployed"
        else:
            negative = True
            if not quick_check:
                max_attempts = 5
                pause = 5
            else:
                max_attempts = 1
                pause = 0
            phrase = "Checking not deployed"
        with loading_animation(phrase=phrase):
            out = _command_loop("docker", self._check_deployed_args, self._deployed_validation,
                                negative=negative, max_attempts=max_attempts, pause=pause)
            if not out[0]:
                raise ValueError(
                    "Not deployed" if should_be_deployed else "Is deployed")

    def deploy(self):
        self.check_deployed(should_be_deployed=False)
        with loading_animation(phrase="Deploying"):
            out = _command_loop("docker", self._deploy_args,
                                self._deploying_validation, max_attempts=1)
            if not out[0]:
                raise ValueError("Error while deploying. Output:\n\n{out[1]}")
        self.check_deployed(should_be_deployed=True)

    def teardown(self):
        self.check_deployed(should_be_deployed=True)
        with loading_animation(phrase="Tearing down"):
            out = _command_loop("docker", self._teardown_args,
                                self._tearing_down_validation, max_attempts=1)
            if not out[0]:
                raise ValueError(
                    f"Error while tearing down. Output:\n\n{out[1]}")
        self.check_deployed(should_be_deployed=False)

    def logs(self, component, follow=False):
        status_cmd = ["docker"] + self._status_args + \
            [f"{self.stack_name}_{self.components_mapping.get(component, component)}"]
        if follow:
            status_cmd.append("-f")
        subprocess.run(status_cmd, check=True)
