"""*The data objects of configuration*

content ...
"""
import os
from typing import Any, Callable, Dict, List, Optional, Union

from ..._utils import YAML
from ..._utils.file_opt import _BaseFileOperation
from ..enums import ConfigLoadingOrder
from ._base import _Checkable, _Config
from ._divide import _BeDividedable, _Dividable, _DivideStrategy
from .apis import (
    HTTP,
    APIParameter,
    HTTPRequest,
    HTTPResponse,
    MockAPI,
    ResponseProperty,
)
from .base import BaseConfig
from .item import IteratorItem
from .template import (
    TemplateConfig,
    TemplateConfigLoadable,
    TemplateConfigLoader,
    TemplateConfigOpts,
    _TemplatableConfig,
)


class MockAPIs(_Config, _Checkable, TemplateConfigOpts, _Dividable):
    """*The **mocked_apis** section*"""

    _template: TemplateConfig
    _base: Optional[BaseConfig]
    _apis: Dict[str, Optional[MockAPI]]

    _configuration: _BaseFileOperation = YAML()
    _need_template_in_config: bool = True
    _template_config_loader: TemplateConfigLoadable

    def __init__(
        self,
        template: Optional[TemplateConfig] = None,
        base: Optional[BaseConfig] = None,
        apis: Dict[str, Optional[MockAPI]] = {},
    ):
        super().__init__()
        self._template = template if template is not None else TemplateConfig()
        self._base = base
        self._apis = apis

        self.divide_strategy: _DivideStrategy = _DivideStrategy()
        self.is_pull: bool = False
        self._base_file_path: str = ""

        self._template_config_loader = TemplateConfigLoader()
        self._template_config_loader.register(self.register_callbacks())

    def __len__(self):
        return len(self.apis.keys())

    def _compare(self, other: "MockAPIs") -> bool:
        return self.base == other.base and self.apis == other.apis

    @property
    def key(self) -> str:
        return "mocked_apis"

    @property
    def base_file_path(self) -> str:
        return self._base_file_path

    @base_file_path.setter
    def base_file_path(self, p: str) -> None:
        self._base_file_path = p

    @property
    def template(self) -> TemplateConfig:
        return self._template

    @template.setter
    def template(self, template: Union[dict, TemplateConfig]) -> None:
        if template is not None:
            if isinstance(template, dict):
                self._template = TemplateConfig().deserialize(data=template)
            elif isinstance(template, TemplateConfig):
                self._template = template
            else:
                raise TypeError("Setter *MockAPIs.template* only accepts dict or TemplateConfig type object.")

    @property
    def base(self) -> Optional[BaseConfig]:
        return self._base

    @base.setter
    def base(self, base: Union[dict, BaseConfig]) -> None:
        if base is not None:
            if isinstance(base, dict):
                self._base = BaseConfig().deserialize(data=base)
            elif isinstance(base, BaseConfig):
                self._base = base
            else:
                raise TypeError("Setter *MockAPIs.base* only accepts dict or BaseConfig type object.")
        else:
            self._base = None

    @property
    def apis(self) -> Dict[str, Optional[MockAPI]]:
        return self._apis

    @apis.setter
    def apis(self, apis: Dict[str, Union[dict, MockAPI]]) -> None:
        if apis is not None:
            if not isinstance(apis, dict):
                raise TypeError("Setter *MockAPIs.apis* only accepts dict or MockAPI type object.")

            ele_types = set(list(map(lambda v: isinstance(v, MockAPI), apis.values())))
            if len(ele_types) > 1:
                raise ValueError("It has multiple types of the data content. Please unify these objects data type.")

            if False in ele_types:
                self._apis = {}
                for api_name, api_config in apis.items():
                    self._apis[api_name] = MockAPI().deserialize(data=(api_config or {}))
            else:
                self._apis = apis  # type: ignore

    @property
    def set_template_in_config(self) -> bool:
        return self._need_template_in_config

    @set_template_in_config.setter
    def set_template_in_config(self, _set: bool) -> None:
        self._need_template_in_config = _set

    @property
    def should_divide(self) -> bool:
        return self.divide_strategy.divide_api

    def serialize(self, data: Optional["MockAPIs"] = None) -> Optional[Dict[str, Any]]:
        template = (data.template if data else None) or self.template
        base = (data.base if data else None) or self.base
        apis = (data.apis if data else None) or self.apis
        if not (template and base and apis):
            return None

        # Process section *base*
        api_info: dict = {
            "base": BaseConfig().serialize(data=base),
            "apis": {},
        }
        if self._need_template_in_config:
            if self.is_pull:
                template.activate = True
                if self.base_file_path:
                    template.values.base_file_path = self.base_file_path
            api_info["template"] = template.serialize()

        # Process section *apis*
        all_mocked_apis = {}  # type: ignore[var-annotated]
        for api_name, api_config in apis.items():
            assert api_config
            self._process_dividing_serialize(
                init_data=all_mocked_apis,
                data_modal=api_config,
                api_name=api_name,
                tag=api_config.tag,
                key=api_name,
            )
        api_info["apis"] = all_mocked_apis

        not_empty_api_config = {}
        for k, v in api_info.items():
            if v:
                not_empty_api_config[k] = v
        return not_empty_api_config

    @property
    def _current_template_at_serialization(self) -> TemplateConfig:
        return self.template

    def _set_serialized_data(
        self, init_data: Dict[str, Any], serialized_data: Optional[Union[str, dict]], key: str = ""
    ) -> None:
        init_data[key] = serialized_data

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["MockAPIs"]:
        """Convert data to **MockAPIs** type object.

        The data structure should be like following:

        * Example data:
        .. code-block:: python

            {
                'base': {'url': '/test/v1'},
                'apis': {
                    'google_home': {
                        'url': '/google',
                        'http': {
                            'request': {
                                'method': 'GET',
                                'parameters': [{'param1': 'val1'}]
                            },
                            'response': {
                                'value': 'This is Google home API.'
                            }
                        }
                    },
                    'test_home': {
                        'url': '/google',
                        'http': {
                            'request': {
                                'method': 'GET',
                                'parameters': [{'param1': 'val1'}]
                            },
                            'response': {
                                'value': '{ "responseCode": "200", "errorMessage": "OK", "content": "This is Test home." }'
                            }
                        },
                        'cookie': [{'TEST': 'cookie_value'}]
                    },
                    'youtube_home': {
                        'url': '/youtube',
                        'http': {
                            'request': {
                                'method': 'GET',
                                'parameters': [{'param1': 'val1'}]
                            },
                            'response': {'value': 'youtube.json'}
                        },
                        'cookie': [{'USERNAME': 'test'}, {'SESSION_EXPIRED': '2023-12-31T00:00:00.000'}]
                    }
                }
            }

        Args:
            data (Dict[str, Any]): Target data to convert.

        Returns:
            A **MockAPIs** type object.

        """
        # Processing section *template*
        template_info = data.get("template", {})
        if not template_info:
            self._need_template_in_config = False
        self.template.absolute_model_key = self.key
        if self.is_pull:
            self.template.activate = True
            if self.base_file_path:
                self.template.values.base_file_path = self.base_file_path
        self.template.deserialize(data=template_info)

        # Processing section *base*
        base_info = data.get("base", None)
        base_config = BaseConfig()
        base_config.absolute_model_key = self.key
        self.base = base_config.deserialize(data=base_info)

        # Processing section *apis*
        mocked_apis_info = data.get("apis", {})
        self._template_config_loader._load_mocked_apis_config(mocked_apis_info)
        return self

    def is_work(self) -> bool:
        under_check = {
            f"{self.absolute_model_key}.<API name>": self.apis,
            self.template.absolute_model_key: self.template,
        }
        if self.base is not None:
            self.base.stop_if_fail = self.stop_if_fail
            under_check[self.base.absolute_model_key] = self.base
        if not self.props_should_not_be_none(under_check=under_check):
            return False

        if self.apis:
            for ak, av in self.apis.items():
                # TODO: Check the key validity about it will be the function naming in Python code
                api_config_is_valid = self.props_should_not_be_none(
                    under_check={
                        f"{self.absolute_model_key}.<API name>": ak,
                        f"{self.absolute_model_key}.{ak}": av,
                    }
                )
                assert av is not None
                av.stop_if_fail = self.stop_if_fail
                if not api_config_is_valid or not av.is_work():
                    return False
        self.template.stop_if_fail = self.stop_if_fail
        return self.template.is_work() and (self.base.is_work() if self.base else True)

    def _set_mocked_apis(self, api_key: str = "", api_config: Optional[MockAPI] = None) -> None:  # type: ignore[override]
        if api_key and api_config:
            print(f"[DEBUG in MockAPIs._set_mocked_apis] api_key: {api_key}")
            print(f"[DEBUG in MockAPIs._set_mocked_apis] api_config: {api_config}")
            self.apis[api_key] = api_config
        else:
            self.apis = {}

    @property
    def _template_config(self) -> TemplateConfig:
        return self.template

    @property
    def _config_file_format(self) -> str:
        return self.template.values.api.config_path_format

    @property
    def _deserialize_as_template_config(self) -> MockAPI:
        mock_api = MockAPI(_current_template=self.template)
        mock_api.absolute_model_key = self.key
        return mock_api

    def _set_template_config(self, config: MockAPI, **kwargs) -> None:  # type: ignore[override]
        # Read YAML config
        mock_api_config_name = os.path.basename(kwargs["path"])
        format_rule_string = self._config_file_format.replace("**", "")
        mock_api_config_key = mock_api_config_name.replace(format_rule_string, "")
        # Set the data model in config
        self.apis[mock_api_config_key] = config

    def get_api_config_by_url(self, url: str, base: Optional[BaseConfig] = None) -> Optional[MockAPI]:
        url = url.replace(base.url, "") if base else url
        for k, v in self._apis.items():
            if v and v.url == url:
                return self._apis[k]
        return None

    def get_all_api_config_by_url(self, url: str, base: Optional[BaseConfig] = None) -> Dict[str, MockAPI]:
        url = url.replace(base.url, "") if base else url
        all_api_configs: Dict[str, MockAPI] = {}
        for k, v in self._apis.items():
            if v and v.url == url:
                all_api_configs[v.http.request.method.upper()] = self._apis[k]  # type: ignore[union-attr,assignment]
        return all_api_configs

    def group_by_url(self) -> Dict[str, List[MockAPI]]:
        apis = self._apis
        aggregated_apis: Dict[str, List[MockAPI]] = {}
        for api_name, api_config in apis.items():
            assert api_config and api_config.url
            one_url_details = aggregated_apis.get(api_config.url, [])
            one_url_details.append(api_config)
            aggregated_apis[api_config.url] = one_url_details
        return aggregated_apis


class APIConfig(_Config, _Checkable):
    """*The entire configuration*"""

    _name: str = ""
    _description: str = ""
    _apis: Optional[MockAPIs]

    _config_file_name: str = "api.yaml"
    _configuration: _BaseFileOperation = YAML()
    _need_template_in_config: bool = True
    _dry_run: bool = True
    _divide_strategy: _DivideStrategy = _DivideStrategy()

    def __init__(self, name: str = "", description: str = "", apis: Optional[MockAPIs] = None):
        self._name = name
        self._description = description
        self._apis = apis

        self.is_pull: bool = False
        self._base_file_path: str = ""

    def __len__(self):
        return len(self._apis) if self._apis else 0

    def _compare(self, other: "APIConfig") -> bool:
        return self.name == other.name and self.description == other.description and self.apis == other.apis

    @property
    def key(self) -> str:
        return ""

    @property
    def _config_operation(self) -> _BaseFileOperation:
        return self._configuration

    def has_apis(self) -> bool:
        return len(self) != 0

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, desc: str) -> None:
        self._description = desc

    @property
    def apis(self) -> Optional[MockAPIs]:
        return self._apis

    @apis.setter
    def apis(self, apis: Union[dict, MockAPIs]) -> None:
        if apis is not None:
            if isinstance(apis, dict):
                self._apis = MockAPIs().deserialize(data=apis)
            elif isinstance(apis, MockAPIs):
                self._apis = apis
            else:
                raise TypeError("Setter *APIConfig.apis* only accepts dict or MockAPIs type object.")

    @property
    def set_template_in_config(self) -> bool:
        return self._need_template_in_config

    @set_template_in_config.setter
    def set_template_in_config(self, _set: bool) -> None:
        self._need_template_in_config = _set

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    @dry_run.setter
    def dry_run(self, d: bool) -> None:
        self._dry_run = d

    @property
    def divide_strategy(self) -> _DivideStrategy:
        return self._divide_strategy

    @divide_strategy.setter
    def divide_strategy(self, d: _DivideStrategy) -> None:
        self._divide_strategy = d

    @property
    def config_file_name(self) -> str:
        return self._config_file_name

    @config_file_name.setter
    def config_file_name(self, n: str) -> None:
        self._config_file_name = n

    @property
    def base_file_path(self) -> str:
        return self._base_file_path

    @base_file_path.setter
    def base_file_path(self, p: str) -> None:
        self._base_file_path = p

    def serialize(self, data: Optional["APIConfig"] = None) -> Optional[Dict[str, Any]]:
        name = (data.name if data else None) or self.name
        description = (data.description if data else None) or self.description
        apis = (data.apis if data else None) or self.apis
        if not apis:
            return None
        apis.is_pull = self.is_pull
        apis.set_template_in_config = self.set_template_in_config
        apis.dry_run = self.dry_run
        apis.divide_strategy = self.divide_strategy
        return {
            "name": name,
            "description": description,
            "mocked_apis": apis.serialize(),
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["APIConfig"]:
        """Convert data to **APIConfig** type object.

        The data structure should be like following:

        * Example data:
        .. code-block:: python

            {
                'name': 'Test mocked API',
                'description': 'This is a test for the usage demonstration.',
                'mocked_apis': {
                    'base': {'url': '/test/v1'},
                    'apis': {
                        'google_home': {
                            'url': '/google',
                            'http': {
                                'request': {
                                    'method': 'GET',
                                    'parameters': [{'param1': 'val1'}]
                                },
                                'response': {
                                    'value': 'This is Google home API.'
                                }
                            }
                        },
                        'test_home': {
                            'url': '/google',
                            'http': {
                                'request': {
                                    'method': 'GET',
                                    'parameters': [{'param1': 'val1'}]
                                },
                                'response': {
                                    'value': '{
                                        "responseCode": "200", "errorMessage": "OK", "content": "This is Test home."
                                    }'
                                }
                            },
                            'cookie': [{'TEST': 'cookie_value'}]
                        },
                        'youtube_home': {
                            'url': '/youtube',
                            'http': {
                                'request': {
                                    'method': 'GET',
                                    'parameters': [{'param1': 'val1'}]
                                },
                                'response': {'value': 'youtube.json'}
                            },
                            'cookie': [{'USERNAME': 'test'}, {'SESSION_EXPIRED': '2023-12-31T00:00:00.000'}]
                        }
                    }
                }
            }

        Args:
            data (Dict[str, Any]): Target data to convert.

        Returns:
            A **APIConfig** type object.

        """
        self.name = data.get("name", None)
        self.description = data.get("description", None)

        mocked_apis = data.get("mocked_apis", None)
        mocked_apis = {"template": {}} if not mocked_apis else mocked_apis
        mock_apis_data_model = MockAPIs()
        mock_apis_data_model.set_template_in_config = self.set_template_in_config
        mock_apis_data_model.config_file_name = self.config_file_name
        mock_apis_data_model.absolute_model_key = self.key
        mock_apis_data_model.divide_strategy = self._divide_strategy
        mock_apis_data_model.is_pull = self.is_pull
        mock_apis_data_model.base_file_path = self.base_file_path
        self.apis = mock_apis_data_model.deserialize(data=mocked_apis)

        return self

    def is_work(self) -> bool:
        if not self.should_not_be_none(
            config_key=f"{self.absolute_model_key}.mocked_apis",
            config_value=self.apis,
        ):
            self._exit_program(
                msg="⚠️  Configuration is invalid.",
                exit_code=1,
            )
        assert self.apis is not None
        self.apis.stop_if_fail = self.stop_if_fail
        return self.apis.is_work()

    def from_yaml(self, path: str, is_pull: bool = False) -> Optional["APIConfig"]:
        self.is_pull = is_pull
        return self.deserialize(data=self._config_operation.read(path))

    def to_yaml(self, path: str) -> None:
        self._config_operation.write(path=path, config=(self.serialize() or {}))
