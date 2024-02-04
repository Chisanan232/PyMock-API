import glob
import os
import pathlib
from typing import List

import pytest

from pymock_api import APIConfig
from pymock_api.model import load_config

from ..._file_utils import MockAPI_Config_Yaml_Path, yaml_factory
from ..._spec import run_test

# [(under_test_path, expected_path)]
DIVIDING_YAML_PATHS: List[tuple] = []


def _get_all_yaml_for_dividing() -> None:
    def _get_path(scenario_folder: str = "", yaml_file_naming: str = "") -> str:
        _path = (
            str(pathlib.Path(__file__).parent.parent.parent),
            "data",
            "divide_test_load",
            scenario_folder,
            yaml_file_naming,
        )
        return os.path.join(*_path)

    different_scenarios_data_folder = os.listdir(_get_path())
    for f in different_scenarios_data_folder:
        yaml_dir = _get_path(scenario_folder=f, yaml_file_naming="api.yaml")
        expected_yaml_dir = _get_path(scenario_folder=f, yaml_file_naming="_expected_api.yaml")
        global DIVIDING_YAML_PATHS
        for yaml_config_path, expected_yaml_config_path in zip(glob.glob(yaml_dir), glob.glob(expected_yaml_dir)):
            one_test_scenario = (yaml_config_path, expected_yaml_config_path)
            DIVIDING_YAML_PATHS.append(one_test_scenario)


_get_all_yaml_for_dividing()


class TestInitFunctions:
    @property
    def not_exist_file_path(self) -> str:
        return "./file_not_exist.yaml"

    @run_test.with_file(yaml_factory)
    def test_load_config(self):
        # Run target function
        loaded_data = load_config(path=MockAPI_Config_Yaml_Path)

        # Verify result
        assert isinstance(loaded_data, APIConfig) and len(loaded_data) != 0, ""
        return "./file_not_exist.yaml"

    @run_test.with_file(yaml_factory)
    def test_load_config_with_not_exist_file(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            # Run target function to test
            load_config(path=self.not_exist_file_path)
            # Verify result
            expected_err_msg = f"The target configuration file {self.not_exist_file_path} doesn't exist."
            assert str(exc_info) == expected_err_msg, f"The error message should be same as '{expected_err_msg}'."

    @pytest.mark.parametrize(("yaml_config_path", "expected_yaml_config_path"), DIVIDING_YAML_PATHS)
    def test_load_config_with_dividing_feature(self, yaml_config_path: str, expected_yaml_config_path: str):
        # Run utility function loads configuration to get config data
        dividing_config = load_config(yaml_config_path)
        # expected_config = load_config(expected_yaml_config_path)

        # Verify detail values
        assert dividing_config is not None
        # assert expected_config is not None

        # # Check basic info
        # assert dividing_config.name == expected_config.name
        # assert dividing_config.description == expected_config.description
        #
        # Check section
        assert dividing_config.apis is not None
        # assert expected_config.apis is not None

        # Check section *base*
        if "no-base" not in yaml_config_path:
            assert dividing_config.apis.base is not None
        #     assert expected_config.apis.base is not None
        #     assert dividing_config.apis.base.serialize() == expected_config.apis.base.serialize()

        # Check section *apis*
        assert dividing_config.apis.apis is not None
        # assert expected_config.apis.apis is not None
        # expected_config_apis = expected_config.apis.apis
        # # Compare the key of all mocked APIs
        # assert dividing_config.apis.apis.keys() == expected_config.apis.apis.keys()
        # # Compare the details of each mocked API
        for api_name, api_config in dividing_config.apis.apis.items():
            print(f"[DEBUG in test] api_name: {api_name}")
            # expected_api_config = expected_config_apis[api_name]
            # assert api_config is not None
            # assert expected_api_config is not None
            # # Check URL
            # assert api_config.url == expected_api_config.url
            # # Check HTTP request
            # assert api_config.http is not None
            # assert expected_api_config.http is not None
            # assert api_config.http.request is not None
            # assert expected_api_config.http.request is not None
            # assert api_config.http.request.method == expected_api_config.http.request.method
            # assert api_config.http.request.parameters == expected_api_config.http.request.parameters
            print(f"[DEBUG in test] api_config.http.request.parameters: {api_config.http.request.parameters}")  # type: ignore
            # print(f"[DEBUG in test] expected_api_config.http.request.parameters: {expected_api_config.http.request.parameters}")
            # assert api_config.http.request.serialize() == expected_api_config.http.request.serialize()
            # Check HTTP response
            # assert api_config.http.response is not None
            # assert expected_api_config.http.response is not None
            # assert api_config.http.response.serialize() == expected_api_config.http.response.serialize()
        assert False
