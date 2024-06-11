import re
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from pymock_api import APIConfig
from pymock_api.command._common.component import SavingConfigComponent
from pymock_api.command.add.component import SubCmdAddComponent
from pymock_api.model import generate_empty_config
from pymock_api.model.cmd_args import SubcmdAddArguments
from pymock_api.model.enums import ResponseStrategy

from ...._values import (
    _Test_Config,
    _Test_Response_Strategy,
    _Test_SubCommand_Add,
    _Test_URL,
)


class FakeSavingConfigComponent(SavingConfigComponent):
    pass


class TestSubCmdAddComponent:
    @pytest.fixture(scope="class")
    def component(self) -> SubCmdAddComponent:
        return SubCmdAddComponent()

    def test_assert_error_with_empty_api_config_path(self, component: SubCmdAddComponent):
        # Mock functions
        FakeSavingConfigComponent.serialize_and_save = MagicMock()

        invalid_args = SubcmdAddArguments(
            subparser_name=_Test_SubCommand_Add,
            config_path="",
            api_path="",
            http_method="",
            parameters=[],
            response_strategy=_Test_Response_Strategy,
            response_value=[""],
            include_template_config=False,
            base_file_path="./",
            dry_run=False,
            divide_api=False,
            divide_http=False,
            divide_http_request=False,
            divide_http_response=False,
        )

        # Run target function to test
        with patch(
            "pymock_api.command.add.component.SavingConfigComponent", return_value=FakeSavingConfigComponent
        ) as mock_saving_config_component:
            with pytest.raises(AssertionError) as exc_info:
                component.process(invalid_args)

            # Verify result
            assert re.search(r"Option '.{1,20}' value cannot be empty.", str(exc_info.value), re.IGNORECASE)
            mock_saving_config_component.assert_not_called()
            FakeSavingConfigComponent.serialize_and_save.assert_not_called()

    @pytest.mark.parametrize(
        ("file_exist", "load_config_result"),
        [
            (False, None),
            (True, generate_empty_config()),
            (True, None),
        ],
    )
    def test_get_api_config(
        self, file_exist: bool, load_config_result: Optional[APIConfig], component: SubCmdAddComponent
    ):
        with patch("pymock_api.command.add.component.load_config", return_value=load_config_result) as mock_load_config:
            with patch("pymock_api.command.add.component.generate_empty_config") as mock_generate_empty_config:
                with patch("os.path.exists", return_value=file_exist) as mock_path_exist:
                    args = SubcmdAddArguments(
                        subparser_name=_Test_SubCommand_Add,
                        config_path=_Test_Config,
                        api_path=_Test_URL,
                        http_method="GET",
                        parameters=[],
                        response_strategy=_Test_Response_Strategy,
                        response_value=["OK"],
                        include_template_config=False,
                        base_file_path="./",
                        dry_run=False,
                        divide_api=False,
                        divide_http=False,
                        divide_http_request=False,
                        divide_http_response=False,
                    )
                    component._get_api_config(args)

                    mock_path_exist.assert_called_once_with(_Test_Config)
                    if file_exist:
                        mock_load_config.assert_called_once_with(_Test_Config)
                        if load_config_result:
                            mock_generate_empty_config.assert_not_called()
                        else:
                            mock_generate_empty_config.assert_called_once()
                    else:
                        mock_load_config.assert_not_called()
                        mock_generate_empty_config.assert_called_once()

    @pytest.mark.parametrize(
        ("http_method", "parameters", "response_strategy", "response_value"),
        [
            (None, [], _Test_Response_Strategy, None),
            (
                "POST",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str"}],
                _Test_Response_Strategy,
                ["This is PyTest response"],
            ),
            (
                "PUT",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str"}],
                ResponseStrategy.OBJECT,
                [
                    {"name": "id", "required": True, "type": "int", "format": None, "items": None},
                    {"name": "name", "required": True, "type": "str", "format": None, "items": None},
                ],
            ),
        ],
    )
    def test_add_valid_api(
        self,
        http_method: Optional[str],
        parameters: List[dict],
        response_strategy: ResponseStrategy,
        response_value: Optional[List[str]],
        component: SubCmdAddComponent,
    ):
        # Mock functions
        FakeSavingConfigComponent.serialize_and_save = MagicMock()

        with patch(
            "pymock_api.command.add.component.SavingConfigComponent", return_value=FakeSavingConfigComponent
        ) as mock_saving_config_component:
            with patch("os.path.exists", return_value=False) as mock_path_exist:
                args = SubcmdAddArguments(
                    subparser_name=_Test_SubCommand_Add,
                    config_path=_Test_Config,
                    api_path=_Test_URL,
                    http_method=http_method,
                    parameters=parameters,
                    response_strategy=response_strategy,
                    response_value=response_value,
                    include_template_config=False,
                    base_file_path="./",
                    dry_run=False,
                    divide_api=False,
                    divide_http=False,
                    divide_http_request=False,
                    divide_http_response=False,
                )
                component.process(args)

                api_config = generate_empty_config()
                api_config = component._generate_api_config(api_config, args)

                mock_path_exist.assert_called_once_with(_Test_Config)
                mock_saving_config_component.assert_called_once()
                FakeSavingConfigComponent.serialize_and_save.assert_called_once_with(
                    path=_Test_Config, config=api_config.serialize()
                )

    @pytest.mark.parametrize(
        ("url_path", "http_method", "parameters", "response_strategy", "response_value"),
        [
            (
                None,
                "POST",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str"}],
                _Test_Response_Strategy,
                ["This is PyTest response"],
            ),
            (
                "",
                "POST",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str"}],
                _Test_Response_Strategy,
                ["This is PyTest response"],
            ),
            (
                _Test_URL,
                "POST",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str", "invalid_key": "val"}],
                _Test_Response_Strategy,
                ["This is PyTest response"],
            ),
            (
                _Test_URL,
                "PUT",
                [{"name": "arg1", "required": False, "default": "val1", "type": "str"}],
                _Test_Response_Strategy,
                [{"invalid data structure": ""}],
            ),
        ],
    )
    def test_add_invalid_api(
        self,
        url_path: str,
        http_method: Optional[str],
        parameters: List[dict],
        response_strategy: ResponseStrategy,
        response_value: Optional[List[str]],
        component: SubCmdAddComponent,
    ):
        # Mock functions
        FakeSavingConfigComponent.serialize_and_save = MagicMock()

        with patch(
            "pymock_api.command.add.component.SavingConfigComponent", return_value=FakeSavingConfigComponent
        ) as mock_saving_config_component:
            with patch("os.path.exists", return_value=False) as mock_path_exist:
                args = SubcmdAddArguments(
                    subparser_name=_Test_SubCommand_Add,
                    config_path=_Test_Config,
                    api_path=url_path,
                    http_method=http_method,
                    parameters=parameters,
                    response_strategy=response_strategy,
                    response_value=response_value,
                    include_template_config=False,
                    base_file_path="./",
                    dry_run=False,
                    divide_api=False,
                    divide_http=False,
                    divide_http_request=False,
                    divide_http_response=False,
                )
                with pytest.raises(SystemExit) as exc_info:
                    component.process(args)
                assert str(exc_info.value) == "1"

                if url_path:
                    mock_path_exist.assert_called_once_with(_Test_Config)
                    mock_saving_config_component.assert_called_once()
                else:
                    mock_path_exist.assert_not_called()
                    mock_saving_config_component.assert_not_called()
                FakeSavingConfigComponent.serialize_and_save.assert_not_called()
