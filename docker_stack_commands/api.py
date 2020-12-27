import itertools
import re
import subprocess
import time
import uuid

import yaml
from zmtools import loading_animation, dummy_context_manager


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

    """Class that represents a Docker stack

    Args:
        stack_yaml_file_locations (list[str]): Locations of the YAML files that specify stack details
        stack_name (str, optional): Name of the stack. If None, generates a random name. Defaults to None.
        components_mapping (dict, optional): A dict mapping friendly name of a component to internal name. Defaults to {}.
        show_loading (bool, optional): If True, show a loading symbol when certain stack commands are run. Defaults to True.

    Attributes:
        stack_name (str): Name of the stack
        stack_yaml_file_locations (list[str]): Locations of the YAML files that specify stack details
        components (set): The names of the components that make up the stack
        components_mapping (dict): A dict mapping friendly name of a component to internal name
    """

    def __init__(self, stack_yaml_file_locations, stack_name=None, components_mapping={}, show_loading=True):
        if show_loading:
            self._cm = loading_animation
        else:
            self._cm = dummy_context_manager
        if stack_name is None:
            stack_name = str(uuid.uuid4()).replace("-", "")
        self.stack_name = stack_name
        self.stack_yaml_file_locations = stack_yaml_file_locations
        components = set()
        for stack_yaml_file_location in self.stack_yaml_file_locations:
            with open(stack_yaml_file_location, "r") as f:
                components.update(
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

    def check_deployed(self, should_be_deployed=False, max_check_attempts=None, pause=None):
        """Check if the stack is deployed

        Args:
            should_be_deployed (bool, optional): Will cause function to throw an excpetion if this criteria is not met. Defaults to False.
            max_check_attempts (int, optional): Max amount of times to keep checking if the stack is fully deployed. If None and should_be_deployed, 2. If None and not should_be_deployed, 5. Defaults to None.
            pause (int, optional): Seconds to pause between checks. If None and should_be_deployed, 3. If None and not should_be_deployed, 5. Defaults to None.

        Raises:
            ValueError: [description]
        """
        if should_be_deployed:
            negative = False
            if max_check_attempts is None:
                max_check_attempts = 2
            if pause is None:
                pause = 3
            phrase = "Checking deployed"
        else:
            negative = True
            if max_check_attempts is None:
                max_check_attempts = 5
            if pause is None:
                pause = 5
            phrase = "Checking not deployed"
        with self._cm(phrase=phrase):
            out = _command_loop("docker", self._check_deployed_args, self._deployed_validation,
                                negative=negative, max_attempts=max_check_attempts, pause=pause)
            if not out[0]:
                raise ValueError(
                    "Not deployed" if should_be_deployed else "Is deployed")

    def deploy(self, max_check_attempts=1):
        """Deploy the stack

        Args:
            max_check_attempts (int, optional): Max amount of times to keep chacking if the stack has deployed. Defaults to 1.

        Raises:
            ValueError: If the stack does not deploy
        """
        self.check_deployed(should_be_deployed=False)
        with self._cm(phrase="Deploying"):
            out = _command_loop("docker", self._deploy_args,
                                self._deploying_validation, max_attempts=max_check_attempts)
            if not out[0]:
                raise ValueError("Error while deploying. Output:\n\n{out[1]}")
        self.check_deployed(should_be_deployed=True)

    def teardown(self, max_check_attempts=1):
        """Teardown the stack

        Args:
            max_check_attempts (int, optional): Max amount of times to keep checking if the stack has been torn down. Defaults to 1.

        Raises:
            ValueError: If the stack does not finish tearing down
        """
        self.check_deployed(should_be_deployed=True)
        with self._cm(phrase="Tearing down"):
            out = _command_loop("docker", self._teardown_args,
                                self._tearing_down_validation, max_attempts=max_check_attempts)
            if not out[0]:
                raise ValueError(
                    f"Error while tearing down. Output:\n\n{out[1]}")
        self.check_deployed(should_be_deployed=False)

    def logs(self, component, follow=False):
        """Print logs of one component of a stack

        Args:
            component (str): The name of the component
            follow (bool, optional): If True, continue following it to stdout. Defaults to False.
        """
        status_cmd = ["docker"] + self._status_args + \
            [f"{self.stack_name}_{self.components_mapping.get(component, component)}"]
        if follow:
            status_cmd.append("-f")
        subprocess.run(status_cmd, check=True)
