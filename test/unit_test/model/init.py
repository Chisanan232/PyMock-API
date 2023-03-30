from argparse import Namespace
from unittest.mock import Mock, patch

from pymock_api.model import DeserializeParsedArgs, deserialize_args

from ..._values import (
    _Bind_Host_And_Port,
    _Generate_Sample,
    _Log_Level,
    _Print_Sample,
    _Sample_File_Path,
    _Test_App_Type,
    _Test_Config,
    _Test_SubCommand_Config,
    _Test_SubCommand_Run,
    _Workers_Amount,
)


@patch.object(DeserializeParsedArgs, "subcommand_run")
def test_deserialize_subcommand_run_args(mock_parser_arguments: Mock):
    namespace_args = {
        "subcommand": _Test_SubCommand_Run,
        "config": _Test_Config,
        "app_type": _Test_App_Type,
        "bind": _Bind_Host_And_Port.value,
        "workers": _Workers_Amount.value,
        "log_level": _Log_Level.value,
    }
    namespace = Namespace(**namespace_args)
    deserialize_args.subcmd_run(namespace)
    mock_parser_arguments.assert_called_once_with(namespace)


@patch.object(DeserializeParsedArgs, "subcommand_config")
def test_deserialize_subcommand_config_args(mock_parser_arguments: Mock):
    namespace_args = {
        "subcommand": _Test_SubCommand_Config,
        "generate_sample": _Generate_Sample,
        "print_sample": _Print_Sample,
        "file_path": _Sample_File_Path,
    }
    namespace = Namespace(**namespace_args)
    deserialize_args.subcmd_config(namespace)
    mock_parser_arguments.assert_called_once_with(namespace)
