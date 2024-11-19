import json
import logging
import re
import sys
from argparse import ArgumentParser, Namespace
from enum import Enum
from typing import Callable, List, Optional, Type, Union
from unittest.mock import MagicMock, Mock, patch

import pytest
from yaml import load as yaml_load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore

from test._values import (
    SubCommand,
    _API_Doc_Source,
    _API_Doc_Source_File,
    _Base_URL,
    _Bind_Host_And_Port,
    _Cmd_Arg_API_Path,
    _Cmd_Arg_HTTP_Method,
    _Default_Base_File_Path,
    _Default_Include_Template_Config,
    _Log_Level,
    _Sample_File_Path,
    _Show_Detail_As_Format,
    _Test_Config,
    _Test_Divide_Api,
    _Test_Divide_Http,
    _Test_Divide_Http_Request,
    _Test_Divide_Http_Response,
    _Test_Dry_Run,
    _Test_HTTP_Method,
    _Test_HTTP_Resp,
    _Test_Request_With_Https,
    _Test_URL,
    _Workers_Amount,
)
from test.unit_test.command._base.process import BaseCommandProcessorTestSpec

from pymock_server._utils.file import Format
from pymock_server._utils.file.operation import YAML
from pymock_server.command._base.process import BaseCommandProcessor
from pymock_server.command.options import get_all_subcommands
from pymock_server.command.process import NoSubCmd, make_command_chain
from pymock_server.command.rest_server.pull.process import SubCmdPull
from pymock_server.command.subcommand import SubCommandLine
from pymock_server.model import (
    ParserArguments,
    SubcmdAddArguments,
    SubcmdCheckArguments,
    SubcmdGetArguments,
    SubcmdPullArguments,
    SubcmdRunArguments,
    deserialize_api_doc_config,
)
from pymock_server.model.api_config.apis import ResponseStrategy
from pymock_server.model.rest_api_doc_config.base_config import set_component_definition
from pymock_server.model.subcmd_common import SysArg
from pymock_server.server import Command, CommandOptions, WSGIServer

from ._test_case import SubCmdPullTestCaseFactory

logger = logging.getLogger(__name__)


class FakeSubCommandLine(Enum):
    PyTest: str = "pytest-subcmd"
    Fake: str = "pytest-duplicated"


_Fake_SubCmd: FakeSubCommandLine = FakeSubCommandLine.PyTest
_Fake_SubCmd_Obj: SysArg = SysArg(subcmd=_Fake_SubCmd)
_Fake_Duplicated_SubCmd: FakeSubCommandLine = FakeSubCommandLine.Fake
_Fake_Duplicated_SubCmd_Obj: SysArg = SysArg(pre_subcmd=None, subcmd=_Fake_Duplicated_SubCmd)
_No_SubCmd_Amt: int = 1
_Fake_Amt: int = 1


def _given_parser_args(
    subcommand: str = None,
    app_type: str = None,
    config_path: str = None,
    swagger_doc_url: str = None,
    stop_if_fail: bool = True,
    get_api_path: str = _Cmd_Arg_API_Path,
) -> Union[SubcmdRunArguments, SubcmdAddArguments, SubcmdCheckArguments, SubcmdGetArguments, ParserArguments]:
    if subcommand == "run":
        return SubcmdRunArguments(
            subparser_structure=SysArg.parse([SubCommand.RestServer, subcommand]),
            app_type=app_type,
            config=_Test_Config,
            bind=_Bind_Host_And_Port.value,
            workers=_Workers_Amount.value,
            log_level=_Log_Level.value,
        )
    elif subcommand == "add":
        return SubcmdAddArguments(
            subparser_structure=SysArg.parse([SubCommand.RestServer, subcommand]),
            config_path=_Sample_File_Path,
            api_path=_Test_URL,
            http_method=_Test_HTTP_Method,
            parameters=[],
            response_strategy=ResponseStrategy.STRING,
            response_value=_Test_HTTP_Resp,
            include_template_config=False,
            base_file_path="./",
            dry_run=False,
            divide_api=False,
            divide_http=False,
            divide_http_request=False,
            divide_http_response=False,
        )
    elif subcommand == "check":
        return SubcmdCheckArguments(
            subparser_structure=SysArg.parse([SubCommand.RestServer, subcommand]),
            config_path=(config_path or _Test_Config),
            swagger_doc_url=swagger_doc_url,
            stop_if_fail=stop_if_fail,
            check_api_path=True,
            check_api_parameters=True,
            check_api_http_method=True,
        )
    elif subcommand == "get":
        return SubcmdGetArguments(
            subparser_structure=SysArg.parse([SubCommand.RestServer, subcommand]),
            config_path=(config_path or _Test_Config),
            show_detail=True,
            show_as_format=Format[_Show_Detail_As_Format.upper()],
            api_path=get_api_path,
            http_method=_Cmd_Arg_HTTP_Method,
        )
    else:
        return ParserArguments(
            subparser_structure=SysArg.parse([]),
        )


def _given_command_option() -> CommandOptions:
    return CommandOptions(bind=_Bind_Host_And_Port.value, workers=_Workers_Amount.value, log_level=_Log_Level.value)


def _given_command(app_type: str) -> Command:
    mock_parser_arg = _given_parser_args(subcommand="run", app_type=app_type)
    mock_cmd_option_obj = _given_command_option()
    return Command(entry_point="SGI tool command", app=mock_parser_arg.app_type, options=mock_cmd_option_obj)


class FakeYAML(YAML):
    pass


class FakeCommandProcess(BaseCommandProcessor):
    responsible_subcommand: SysArg = _Fake_SubCmd_Obj

    def _parse_process(self, parser: ArgumentParser, cmd_args: Optional[List[str]] = None) -> ParserArguments:
        return

    def _run(self, parser: ArgumentParser, args: ParserArguments) -> None:
        pass


class TestSubCmdProcessChain:
    @pytest.fixture(scope="class")
    def cmd_processor(self) -> FakeCommandProcess:
        return FakeCommandProcess()

    def test_next(self, cmd_processor: FakeCommandProcess):
        next_cmd = cmd_processor._next
        assert (next_cmd != cmd_processor) and (next_cmd is not cmd_processor)

    def test_next_exceed_length(self, cmd_processor: FakeCommandProcess):
        with pytest.raises(StopIteration):
            for _ in range(len(make_command_chain()) + 1):
                assert cmd_processor._next

    @pytest.mark.parametrize(
        ("subcmd", "expected_result"),
        [
            (_Fake_SubCmd_Obj, True),
            (_Fake_Duplicated_SubCmd_Obj, False),
        ],
    )
    def test_is_responsible(self, subcmd: SysArg, expected_result: bool, cmd_processor: FakeCommandProcess):
        is_responsible = cmd_processor._is_responsible(subcmd=subcmd)
        assert is_responsible is expected_result

    @pytest.mark.parametrize(
        ("chk_result", "should_dispatch"),
        [
            (True, False),
            (False, True),
        ],
    )
    def test_process(self, chk_result: bool, should_dispatch: bool, cmd_processor: FakeCommandProcess):
        cmd_processor._is_responsible = MagicMock(return_value=chk_result)
        cmd_processor._run = MagicMock()

        arg = ParserArguments(subparser_structure=_Fake_SubCmd_Obj)
        cmd_parser = Mock()
        cmd_processor.process(parser=cmd_parser, args=arg)

        cmd_processor._is_responsible.assert_called_once_with(subcmd=None)
        if should_dispatch:
            cmd_processor._run.assert_not_called()
        else:
            cmd_processor._run.assert_called_once_with(parser=cmd_parser, args=arg)

    @patch("copy.copy")
    def test_copy(self, mock_copy: Mock, cmd_processor: FakeCommandProcess):
        cmd_processor.copy()
        mock_copy.assert_called_once_with(cmd_processor)


class TestNoSubCmd(BaseCommandProcessorTestSpec):
    @pytest.fixture(scope="function")
    def cmd_ps(self) -> NoSubCmd:
        return NoSubCmd()

    def test_with_command_processor(self, object_under_test: Callable, **kwargs):
        with patch.object(sys, "argv", self._given_command_line()):
            kwargs = {
                "cmd_ps": object_under_test,
            }
            self._test_process(**kwargs)

    def test_with_run_entry_point(self, entry_point_under_test: Callable, **kwargs):
        with patch.object(sys, "argv", self._given_command_line()):
            kwargs = {
                "cmd_ps": entry_point_under_test,
            }
            self._test_process(**kwargs)

    def _test_process(self, cmd_ps: Callable):
        mock_parser_arg = _given_parser_args(subcommand=None)
        command = _given_command(app_type="Python web library")
        command.run = MagicMock()
        cmd_parser = Mock()

        with patch.object(WSGIServer, "generate", return_value=command) as mock_sgi_generate:
            cmd_ps(cmd_parser, mock_parser_arg)
            mock_sgi_generate.assert_not_called()
            command.run.assert_not_called()

    def _given_command_line(self) -> List[str]:
        return []

    def _given_cmd_args_namespace(self) -> Namespace:
        args_namespace = Namespace()
        args_namespace.subcommand = None
        return args_namespace

    def _given_subcmd(self) -> Optional[SysArg]:
        return SysArg(subcmd=SubCommandLine.Base)

    def _expected_argument_type(self) -> Type[Namespace]:
        return Namespace


# # With valid configuration
# SubCmdGetTestCaseFactory.load(get_api_path="/foo-home", is_valid_config=True, exit_code=0)
# SubCmdGetTestCaseFactory.load(get_api_path="/not-exist-api", is_valid_config=True, exit_code=1)
#
# # With invalid configuration
# SubCmdGetTestCaseFactory.load(get_api_path="/foo-home", is_valid_config=False, acceptable_error=True, exit_code=0)
# SubCmdGetTestCaseFactory.load(get_api_path="/foo-home", is_valid_config=False, acceptable_error=False, exit_code=1)
# SubCmdGetTestCaseFactory.load(get_api_path="/not-exist-api", is_valid_config=False, acceptable_error=True, exit_code=1)
# SubCmdGetTestCaseFactory.load(get_api_path="/not-exist-api", is_valid_config=False, acceptable_error=False, exit_code=1)
#
# SUBCMD_GET_TEST_CASE = SubCmdGetTestCaseFactory.get_test_case()


SubCmdPullTestCaseFactory.load()
SUBCMD_PULL_TEST_CASE = SubCmdPullTestCaseFactory.get_test_case()


class TestSubCmdPull(BaseCommandProcessorTestSpec):
    @pytest.fixture(scope="function")
    def cmd_ps(self) -> SubCmdPull:
        return SubCmdPull()

    @pytest.mark.parametrize(
        ("swagger_config", "dry_run", "expected_config"),
        SUBCMD_PULL_TEST_CASE,
    )
    def test_with_command_processor(
        self, swagger_config: str, dry_run: bool, expected_config: str, object_under_test: Callable
    ):
        kwargs = {
            "swagger_config": swagger_config,
            "dry_run": dry_run,
            "expected_config": expected_config,
            "cmd_ps": object_under_test,
        }
        self._test_process(**kwargs)

    @pytest.mark.parametrize(
        ("swagger_config", "dry_run", "expected_config"),
        SUBCMD_PULL_TEST_CASE,
    )
    def test_with_run_entry_point(
        self, swagger_config: str, dry_run: bool, expected_config: str, entry_point_under_test: Callable
    ):
        kwargs = {
            "swagger_config": swagger_config,
            "dry_run": dry_run,
            "expected_config": expected_config,
            "cmd_ps": entry_point_under_test,
        }
        self._test_process(**kwargs)

    def _test_process(self, swagger_config: str, dry_run: bool, expected_config: str, cmd_ps: Callable):
        FakeYAML.write = MagicMock()
        base_url = _Base_URL if ("has-base" in swagger_config and "has-base" in expected_config) else ""
        mock_parser_arg = SubcmdPullArguments(
            subparser_structure=SysArg.parse([SubCommand.RestServer, SubCommand.Pull]),
            request_with_https=_Test_Request_With_Https,
            source=_API_Doc_Source,
            source_file=_API_Doc_Source_File,
            config_path=_Test_Config,
            base_url=base_url,
            base_file_path=_Default_Base_File_Path,
            include_template_config=_Default_Include_Template_Config,
            dry_run=dry_run,
            divide_api=_Test_Divide_Api,
            divide_http=_Test_Divide_Http,
            divide_http_request=_Test_Divide_Http_Request,
            divide_http_response=_Test_Divide_Http_Response,
        )
        cmd_parser = Mock()

        with open(swagger_config, "r") as file:
            swagger_json_data = json.loads(file.read())

        with open(expected_config, "r") as file:
            expected_config_data = yaml_load(file, Loader=Loader)

        set_component_definition(swagger_json_data.get("definitions", {}))
        with patch("sys.argv", self._given_command_line()):
            with patch(
                "pymock_server.command._common.component.YAML", return_value=FakeYAML
            ) as mock_instantiate_writer:
                with patch(
                    "pymock_server.command.rest_server.pull.component.URLLibHTTPClient.request",
                    return_value=swagger_json_data,
                ) as mock_swagger_request:
                    # Run target function
                    logger.debug(f"run target function: {cmd_ps}")
                    cmd_ps(cmd_parser, mock_parser_arg)

                    mock_instantiate_writer.assert_called_once()
                    mock_swagger_request.assert_called_once_with(method="GET", url=f"http://{_API_Doc_Source}")

                    # Run one core logic of target function
                    under_test_api_config = deserialize_api_doc_config(swagger_json_data).to_api_config(
                        mock_parser_arg.base_url
                    )
                    under_test_api_config.set_template_in_config = False
                    under_test_config_data = under_test_api_config.serialize()
                    assert expected_config_data["name"] == under_test_config_data["name"]
                    assert expected_config_data["description"] == under_test_config_data["description"]
                    assert len(expected_config_data["mocked_apis"].keys()) == len(
                        under_test_config_data["mocked_apis"].keys()
                    )
                    assert len(expected_config_data["mocked_apis"]["apis"].keys()) == len(
                        under_test_config_data["mocked_apis"]["apis"].keys()
                    )
                    expected_config_data_keys = sorted(expected_config_data["mocked_apis"]["apis"].keys())
                    under_test_config_data_keys = sorted(under_test_config_data["mocked_apis"]["apis"].keys())
                    for expected_key, under_test_key in zip(expected_config_data_keys, under_test_config_data_keys):
                        assert expected_key == under_test_key
                        expected_api_config = expected_config_data["mocked_apis"]["apis"][expected_key]
                        under_test_api_config = under_test_config_data["mocked_apis"]["apis"][under_test_key]
                        if expected_key != "base":
                            # Verify mock API URL
                            assert expected_api_config["url"] == under_test_api_config["url"]
                            # Verify mock API request properties - HTTP method
                            assert expected_api_config["http"]["request"] is not None
                            assert under_test_api_config["http"]["request"] is not None
                            assert (
                                expected_api_config["http"]["request"]["method"]
                                == under_test_api_config["http"]["request"]["method"]
                            )
                            # Verify mock API request properties - request parameters
                            assert (
                                expected_api_config["http"]["request"]["parameters"]
                                == under_test_api_config["http"]["request"]["parameters"]
                            )
                            # Verify mock API response properties
                            assert (
                                expected_api_config["http"]["response"]["strategy"]
                                == under_test_api_config["http"]["response"]["strategy"]
                            )
                            assert expected_api_config["http"]["response"].get("value", None) == under_test_api_config[
                                "http"
                            ]["response"].get("value", None)
                            assert expected_api_config["http"]["response"].get("path", None) == under_test_api_config[
                                "http"
                            ]["response"].get("path", None)
                            assert expected_api_config["http"]["response"].get(
                                "properties", None
                            ) == under_test_api_config["http"]["response"].get("properties", None)
                        else:
                            # Verify base info
                            assert expected_api_config == under_test_api_config

                    if mock_parser_arg.dry_run:
                        if len(str(expected_config_data)) > 1000:
                            FakeYAML.write.assert_called_once_with(
                                path="dry-run_result.yaml", config=expected_config_data, mode="w+"
                            )
                        else:
                            FakeYAML.write.assert_not_called()
                    else:
                        FakeYAML.write.assert_called_once_with(
                            path=_Test_Config, config=expected_config_data, mode="w+"
                        )

    def _given_command_line(self) -> List[str]:
        return ["rest-server", "pull"]

    def _given_cmd_args_namespace(self) -> Namespace:
        args_namespace = Namespace()
        args_namespace.subcommand = SubCommand.RestServer
        setattr(args_namespace, SubCommand.RestServer, SubCommand.Pull)
        args_namespace.request_with_https = _Test_Request_With_Https
        args_namespace.source = _API_Doc_Source
        args_namespace.source_file = _API_Doc_Source_File
        args_namespace.base_url = _Base_URL
        args_namespace.base_file_path = _Default_Base_File_Path
        args_namespace.config_path = _Test_Config
        args_namespace.include_template_config = _Default_Include_Template_Config
        args_namespace.dry_run = _Test_Dry_Run
        args_namespace.divide_api = _Test_Divide_Api
        args_namespace.divide_http = _Test_Divide_Http
        args_namespace.divide_http_request = _Test_Divide_Http_Request
        args_namespace.divide_http_response = _Test_Divide_Http_Response
        return args_namespace

    def _given_subcmd(self) -> Optional[SysArg]:
        return SysArg(
            pre_subcmd=SysArg(pre_subcmd=SysArg(subcmd=SubCommandLine.Base), subcmd=SubCommandLine.RestServer),
            subcmd=SubCommandLine.Pull,
        )

    def _expected_argument_type(self) -> Type[SubcmdPullArguments]:
        return SubcmdPullArguments


def test_make_command_chain():
    assert len(get_all_subcommands()) == len(make_command_chain()) - _No_SubCmd_Amt - _Fake_Amt


def test_make_command_chain_if_duplicated_subcmd():
    class FakeCmdPS(BaseCommandProcessor):
        responsible_subcommand: SysArg = _Fake_Duplicated_SubCmd_Obj

        def run(self, args: ParserArguments) -> None:
            pass

    class FakeDuplicatedCmdPS(BaseCommandProcessor):
        responsible_subcommand: SysArg = _Fake_Duplicated_SubCmd_Obj

        def run(self, args: ParserArguments) -> None:
            pass

    with pytest.raises(ValueError) as exc_info:
        make_command_chain()
    assert re.search(r"subcommand.{1,64}has been used", str(exc_info.value), re.IGNORECASE)

    # Remove the invalid object for test could run finely.
    from pymock_server.command._base.process import CommandProcessChain

    CommandProcessChain.pop(-1)
