import fnmatch
import glob
import os
import pathlib
from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union

from ..._utils.file_opt import YAML, _BaseFileOperation
from ...model.enums import (
    ConfigLoadingOrder,
    ConfigLoadingOrderKey,
    set_loading_function,
)
from ._base import SelfType, _Checkable, _Config


@dataclass(eq=False)
class LoadConfig(_Config, _Checkable):
    includes_apis: bool = field(default=True)
    order: List[ConfigLoadingOrder] = field(default_factory=list)

    _default_order: List[ConfigLoadingOrder] = field(init=False, repr=False)
    _absolute_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._default_order = [o for o in ConfigLoadingOrder]
        self._convert_order()

    def _convert_order(self) -> None:
        if self.order:
            is_str = list(map(lambda e: isinstance(e, str), self.order))
            if True in is_str:
                self.order = [ConfigLoadingOrder.to_enum(o) for o in self.order]
        else:
            self.order = self._default_order

    def _compare(self, other: "LoadConfig") -> bool:
        return self.includes_apis == other.includes_apis and self.order == other.order

    @property
    def key(self) -> str:
        return "load_config"

    def serialize(self, data: Optional["LoadConfig"] = None) -> Optional[Dict[str, Any]]:
        includes_apis: bool = self._get_prop(data, prop="includes_apis")
        order: List[Union[str, ConfigLoadingOrder]] = self._get_prop(data, prop="order")
        return {
            "includes_apis": includes_apis,
            "order": [o.value if isinstance(o, ConfigLoadingOrder) else o for o in order],
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["LoadConfig"]:
        self.includes_apis = data.get("includes_apis", True)
        self.order = [ConfigLoadingOrder.to_enum(o) for o in (data.get("order", self._default_order) or [])]
        return self

    def is_work(self) -> bool:
        if not self.props_should_not_be_none(
            under_check={
                f"{self.absolute_model_key}.includes_apis": self.includes_apis,
                f"{self.absolute_model_key}.order": self.order,
            },
        ):
            return False
        if self.order:
            for o in self.order:
                assert self.should_be_valid(
                    config_key=f"{self.absolute_model_key}.order",
                    config_value=o,
                    criteria=[c for c in ConfigLoadingOrder],
                )
        return True


@dataclass(eq=False)
class TemplateSetting(_Config, _Checkable, ABC):
    config_path_format: str = field(default_factory=str)

    _absolute_key: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.config_path_format:
            self.config_path_format = self._default_config_path_format

    def _compare(self, other: "TemplateSetting") -> bool:
        return self.config_path_format == other.config_path_format

    def serialize(self, data: Optional["TemplateSetting"] = None) -> Optional[Dict[str, Any]]:
        config_path_format: str = self._get_prop(data, prop="config_path_format")
        return {
            "config_path_format": config_path_format,
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["TemplateSetting"]:
        self.config_path_format = data.get("config_path_format", self._default_config_path_format)
        return self

    @property
    @abstractmethod
    def _default_config_path_format(self) -> str:
        pass

    def is_work(self) -> bool:
        # TODO: Check the path format
        return True


class TemplateAPI(TemplateSetting):
    @property
    def key(self) -> str:
        return "api"

    @property
    def _default_config_path_format(self) -> str:
        return "**-api.yaml"


class TemplateHTTP(TemplateSetting):
    @property
    def key(self) -> str:
        return "http"

    @property
    def _default_config_path_format(self) -> str:
        return "**-http.yaml"


class TemplateRequest(TemplateSetting):
    @property
    def key(self) -> str:
        return "request"

    @property
    def _default_config_path_format(self) -> str:
        return "**-request.yaml"


class TemplateResponse(TemplateSetting):
    @property
    def key(self) -> str:
        return "response"

    @property
    def _default_config_path_format(self) -> str:
        return "**-response.yaml"


@dataclass(eq=False)
class TemplateValues(_Config, _Checkable):
    base_file_path: str = field(default="./")
    api: TemplateAPI = field(default_factory=TemplateAPI)
    http: TemplateHTTP = field(default_factory=TemplateHTTP)
    request: TemplateRequest = field(default_factory=TemplateRequest)
    response: TemplateResponse = field(default_factory=TemplateResponse)

    _absolute_key: str = field(init=False, repr=False)

    def _compare(self, other: "TemplateValues") -> bool:
        return (
            self.base_file_path == other.base_file_path
            and self.api == other.api
            and self.http == other.http
            and self.request == other.request
            and self.response == other.response
        )

    @property
    def key(self) -> str:
        return "values"

    def serialize(self, data: Optional["TemplateValues"] = None) -> Optional[Dict[str, Any]]:
        base_file_path: str = self._get_prop(data, prop="base_file_path")
        api = self.api or self._get_prop(data, prop="api")
        http = self.http or self._get_prop(data, prop="http")
        request = self.request or self._get_prop(data, prop="request")
        response = self.response or self._get_prop(data, prop="response")
        if not (api and request and response):
            # TODO: Should raise exception?
            return None
        return {
            "base_file_path": base_file_path,
            "api": api.serialize(),
            "http": http.serialize(),
            "request": request.serialize(),
            "response": response.serialize(),
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["TemplateValues"]:
        self.base_file_path = data.get("base_file_path", "./")

        template_api = TemplateAPI()
        template_api.absolute_model_key = self.key
        self.api = template_api.deserialize(data.get("api", {}))

        template_http = TemplateHTTP()
        template_http.absolute_model_key = self.key
        self.http = template_http.deserialize(data.get("http", {}))

        template_request = TemplateRequest()
        template_request.absolute_model_key = self.key
        self.request = template_request.deserialize(data.get("request", {}))

        template_response = TemplateResponse()
        template_response.absolute_model_key = self.key
        self.response = template_response.deserialize(data.get("response", {}))
        return self

    def is_work(self) -> bool:
        # TODO: Check the path format
        self.api.stop_if_fail = self.stop_if_fail
        self.http.stop_if_fail = self.stop_if_fail
        self.request.stop_if_fail = self.stop_if_fail
        self.response.stop_if_fail = self.stop_if_fail
        return self.api.is_work() and self.http.is_work() and self.request.is_work() and self.response.is_work()


@dataclass(eq=False)
class TemplateApply(_Config, _Checkable):
    api: List[Union[str, Dict[str, List[str]]]] = field(default_factory=list)

    _absolute_key: str = field(init=False, repr=False)

    def _compare(self, other: "TemplateApply") -> bool:
        return self.api == other.api

    @property
    def key(self) -> str:
        return "apply"

    def serialize(self, data: Optional["TemplateApply"] = None) -> Optional[Dict[str, Any]]:
        api: str = self._get_prop(data, prop="api")
        return {
            "api": api,
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["TemplateApply"]:
        self.api = data.get("api")  # type: ignore[assignment]
        return self

    def is_work(self) -> bool:
        if self.api is None or len(self.api) == 0:
            return True
        else:
            all_ele_is_str = list(map(lambda a: isinstance(a, str), self.api))
            all_ele_is_dict = list(map(lambda a: isinstance(a, dict), self.api))
            ele_is_str = set(all_ele_is_str)
            ele_is_dict = set(all_ele_is_dict)
            if len(ele_is_str) == 1 and len(ele_is_dict) == 1 and (True in ele_is_str or True in ele_is_dict):
                return True
        return False


@dataclass(eq=False)
class TemplateConfig(_Config, _Checkable):
    """The data model which could be set details attribute by section *template*."""

    activate: bool = field(default=False)
    load_config: LoadConfig = field(default_factory=LoadConfig)
    values: TemplateValues = field(default_factory=TemplateValues)
    apply: TemplateApply = field(default_factory=TemplateApply)

    _absolute_key: str = field(init=False, repr=False)

    def _compare(self, other: "TemplateConfig") -> bool:
        return (
            self.activate == other.activate
            and self.load_config == other.load_config
            and self.values == other.values
            and self.apply == other.apply
        )

    @property
    def key(self) -> str:
        return "template"

    def serialize(self, data: Optional["TemplateConfig"] = None) -> Optional[Dict[str, Any]]:
        activate: bool = self.activate or self._get_prop(data, prop="activate")
        load_config: LoadConfig = self.load_config or self._get_prop(data, prop="load_config")
        values: TemplateValues = self.values or self._get_prop(data, prop="values")
        apply: TemplateApply = self.apply or self._get_prop(data, prop="apply")
        if not (values and apply and activate is not None):
            # TODO: Should it ranse an exception outside?
            return None
        return {
            "activate": activate,
            "load_config": load_config.serialize(),
            "values": values.serialize(),
            "apply": apply.serialize(),
        }

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["TemplateConfig"]:
        self.activate = data.get("activate", False)

        load_config = LoadConfig()
        load_config.absolute_model_key = self.key
        self.load_config = load_config.deserialize(data.get("load_config", {}))

        template_values = TemplateValues()
        template_values.absolute_model_key = self.key
        self.values = template_values.deserialize(data.get("values", {}))

        template_apply = TemplateApply()
        template_apply.absolute_model_key = self.key
        self.apply = template_apply.deserialize(data.get("apply", {}))
        return self

    def is_work(self) -> bool:
        if not self.props_should_not_be_none(
            under_check={
                f"{self.absolute_model_key}.activate": self.activate,
            },
            accept_empty=False,
        ):
            return False
        if not self.props_should_not_be_none(
            under_check={
                f"{self.absolute_model_key}.load_config": self.load_config,
                f"{self.absolute_model_key}.values": self.values,
            },
        ):
            return False
        self.load_config.stop_if_fail = self.stop_if_fail
        self.values.stop_if_fail = self.stop_if_fail
        if self.apply:
            self.apply.stop_if_fail = self.stop_if_fail
        return (
            isinstance(self.activate, bool)
            and self.load_config.is_work()
            and self.values.is_work()
            and (self.apply.is_work() if self.apply else True)
        )


class TemplateConfigOpts(metaclass=ABCMeta):
    _config_file_name: str = "api.yaml"

    def register_callbacks(self) -> "TemplateConfigOpts":
        return self
        # return {
        #     "_template_config": self._template_config,
        #     "_config_file_format": self._config_file_format,
        #     "_deserialize_as_template_config": self._deserialize_as_template_config,
        #     "_set_template_config": self._set_template_config,
        # }

    @property
    def config_file_name(self) -> str:
        return self._config_file_name

    @config_file_name.setter
    def config_file_name(self, n: str) -> None:
        self._config_file_name = n

    @property
    @abstractmethod
    def _template_config(self) -> TemplateConfig:
        pass

    @property
    @abstractmethod
    def _config_file_format(self) -> str:
        pass

    @property
    @abstractmethod
    def _deserialize_as_template_config(self) -> "_TemplatableConfig":
        pass

    @abstractmethod
    def _set_template_config(self, config: _Config, **kwargs) -> None:
        pass

    @abstractmethod
    def _set_mocked_apis(self, api_key: str = "", api_config: Optional[_Config] = None) -> None:
        pass


class TemplateConfigLoadable:
    """The data model which could load template configuration."""

    _configuration: _BaseFileOperation = YAML()

    _valid_loader_keys: List[str] = [k.value for k in ConfigLoadingOrderKey]
    # _loaders: Dict[str, "TemplateConfigLoadable"] = {}

    _template_config_opts: TemplateConfigOpts

    def __init__(self):
        # self._register_loader()  # FIXME: This code would be activated after refactoring done.

        # self._load_mocked_apis_from_data = self._loaders[ConfigLoadingOrderKey.APIs.value].load_config
        self._load_mocked_apis_from_data = None  # Let subclass *TemplateConfigLoaderWithAPIConfig* to set the callback.
        set_loading_function(
            # apis=self._load_mocked_apis_from_data,
            apply=self._load_templatable_config_by_apply,
            file=self._load_templatable_config,
        )

    # def _register_loader(self, key: str) -> None:
    #     if key not in self._valid_loader_keys:
    #         raise KeyError(
    #             f"Loader key *{key}* is not valid. Please use"
    #             f"*{', '.join(self._valid_loader_keys)}* to set the key of loader."
    #         )
    #     self._loaders[key] = self

    def register(self, template_config_ops: TemplateConfigOpts) -> None:
        self._template_config_opts = template_config_ops

    # @property
    # # @abstractmethod    // FIXME: Would be activated after refactoring.
    # def _register_load_by_key(self) -> str:
    #     return "apis"  # FIXME: Would be modify as *pass* after refactoring has done.

    # @abstractmethod    // FIXME: Would be activated after refactoring.
    def load_config(self, *args, **kwargs) -> None:
        pass

    def _load_mocked_apis_config(self, mocked_apis_data: dict) -> None:
        loading_order = self._template_config_opts._template_config.load_config.order

        if self._template_config_opts._template_config.load_config.includes_apis:
            if (ConfigLoadingOrder.APIs not in loading_order) or (
                ConfigLoadingOrder.APIs in loading_order and not self._template_config_opts._template_config.activate
            ):
                self._load_mocked_apis_from_data(mocked_apis_data)

        if self._template_config_opts._template_config.activate:
            for load_config in loading_order:
                args = (mocked_apis_data,)
                args = load_config.get_loading_function_args(*args)  # type: ignore[assignment]
                load_config.get_loading_function()(*args)

    def _load_templatable_config(self) -> None:
        customize_config_file_format = "**"
        config_file_format = f"[!_**]{customize_config_file_format}"
        # all_paths = glob.glob(f"{self._base_path}**/[!_*]*.yaml", recursive=True)
        config_base_path = self._template_config_opts._template_config.values.base_file_path
        all_paths = glob.glob(str(pathlib.Path(config_base_path, config_file_format)))
        api_config_path = str(pathlib.Path(config_base_path, self._template_config_opts.config_file_name))
        if os.path.exists(api_config_path):
            all_paths.remove(api_config_path)
        for path in all_paths:
            if os.path.isdir(path):
                # Has tag as directory
                for path_with_tag in glob.glob(str(pathlib.Path(path, self._template_config_opts._config_file_format))):
                    # In the tag directory, it's config
                    self._deserialize_and_set_template_config(path_with_tag)
            else:
                assert os.path.isfile(path) is True
                if fnmatch.fnmatch(path, self._template_config_opts._config_file_format):
                    # Doesn't have tag, it's config
                    self._deserialize_and_set_template_config(path)

    def _load_templatable_config_by_apply(self) -> None:
        if self._template_config_opts._template_config.apply:
            apply_apis = self._template_config_opts._template_config.apply.api
            all_ele_is_dict = list(map(lambda e: isinstance(e, dict), apply_apis))
            config_path_format = self._template_config_opts._config_file_format
            config_base_path = self._template_config_opts._template_config.values.base_file_path
            if False in all_ele_is_dict:
                # no tag API
                for api in apply_apis:
                    assert isinstance(api, str)
                    api_config = config_path_format.replace("**", api)
                    config_path = str(pathlib.Path(config_base_path, api_config))
                    self._deserialize_and_set_template_config(config_path)
            else:
                # API with tag
                for tag_apis in apply_apis:
                    assert isinstance(tag_apis, dict)
                    for tag, apis in tag_apis.items():
                        for api in apis:
                            api_config = config_path_format.replace("**", api)
                            config_path = str(pathlib.Path(config_base_path, tag, api_config))
                            self._deserialize_and_set_template_config(config_path)

    # @property
    # @abstractmethod
    # def _template_config(self) -> TemplateConfig:
    #     pass

    # @property
    # @abstractmethod
    # def _config_file_format(self) -> str:
    #     pass

    def _deserialize_and_set_template_config(self, path: str) -> None:
        config = self._deserialize_template_config(path)
        assert config is not None, "Configuration should not be empty."
        args = {
            "path": path,
        }
        self._template_config_opts._set_template_config(config, **args)

    def _deserialize_template_config(self, path: str) -> Optional[_Config]:
        # Read YAML config
        yaml_config = self._configuration.read(path)
        # Deserialize YAML config content as PyMock data model
        config = self._template_config_opts._deserialize_as_template_config
        config.base_file_path = str(pathlib.Path(path).parent)
        config.config_path = pathlib.Path(path).name
        return config.deserialize(yaml_config)

    # @property
    # @abstractmethod
    # def _deserialize_as_template_config(self) -> "_TemplatableConfig":
    #     pass
    #
    # @abstractmethod
    # def _set_template_config(self, config: _Config, **kwargs) -> None:
    #     pass


class TemplateConfigLoaderWithAPIConfig(TemplateConfigLoadable):
    def __init__(self):
        super().__init__()
        # self._register_loader(key=ConfigLoadingOrderKey.APIs.value)

        self._load_mocked_apis_from_data = self.load_config
        set_loading_function(
            apis=self._load_mocked_apis_from_data,
        )

    # @property
    # def _register_load_by_key(self) -> str:
    #     return ConfigLoadingOrderKey.APIs.value

    def load_config(self, mocked_apis_data: dict) -> None:
        self._template_config_opts._set_mocked_apis()
        if mocked_apis_data:
            for mock_api_name in mocked_apis_data.keys():
                api_config = self._template_config_opts._deserialize_as_template_config
                api_config.config_path = f"{mock_api_name}{api_config.config_file_tail}.yaml"
                print(f"[DEBUG in TemplateConfigLoaderWithAPIConfig.load_config] mock_api_name: {mock_api_name}")
                print(f"[DEBUG in TemplateConfigLoaderWithAPIConfig.load_config] api_config: {api_config}")
                self._template_config_opts._set_mocked_apis(
                    api_key=mock_api_name,
                    api_config=api_config.deserialize(data=mocked_apis_data.get(mock_api_name, None)),
                )

    # @abstractmethod
    # def _set_mocked_apis(self, api_key: str = "", api_config: Optional[_Config] = None) -> None:
    #     pass


class TemplateConfigLoader(TemplateConfigLoadable):
    """The layer for extending all the configuration loaders"""

    # _loaders: Dict[str, "TemplateConfigLoadable"] = {
    #     ConfigLoadingOrderKey.APIs.value: TemplateConfigLoaderWithAPIConfig(),
    # }
    _loaders: Dict[str, "TemplateConfigLoadable"] = {}

    def __init__(self):
        super().__init__()
        self._loaders: Dict[str, "TemplateConfigLoadable"] = {
            ConfigLoadingOrderKey.APIs.value: TemplateConfigLoaderWithAPIConfig(),
        }

    def register(self, template_config_ops: TemplateConfigOpts) -> None:
        super().register(template_config_ops)
        for k, v in self._loaders.items():
            v.register(template_config_ops)
            if k == ConfigLoadingOrderKey.APIs.value:
                self._load_mocked_apis_from_data = self._loaders[k].load_config
                set_loading_function(
                    apis=self._load_mocked_apis_from_data,
                )


@dataclass(eq=False)
class _TemplatableConfig(_Config, ABC):
    apply_template_props: bool = field(default=True)

    # The settings which could be set by section *template* or override the values
    base_file_path: str = field(default_factory=str)
    config_path: str = field(default_factory=str)
    config_file_tail: str = field(default_factory=str)
    config_path_format: str = field(default_factory=str)

    _default_base_file_path: str = field(default="./")
    _absolute_key: str = field(init=False, repr=False)

    # Attributes for inner usage
    _current_template: TemplateConfig = field(default_factory=TemplateConfig)
    _has_apply_template_props_in_config: bool = field(default=False)

    # Component for inner usage
    _configuration: _BaseFileOperation = field(default_factory=YAML)

    def _compare(self, other: SelfType) -> bool:
        return self.apply_template_props == other.apply_template_props

    def serialize(self, data: Optional[SelfType] = None) -> Optional[Dict[str, Any]]:
        apply_template_props: bool = self._get_prop(data, prop="apply_template_props")
        if self._has_apply_template_props_in_config:
            return {
                "apply_template_props": apply_template_props,
            }
        else:
            return {}

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional[SelfType]:
        def _update_template_prop(key: Any) -> None:
            value = data.get(key, None)
            if value is not None:
                self._has_apply_template_props_in_config = True
                # Note: Override the value which be set by upper layer from template config
                setattr(self, key, value)

        _update_template_prop("apply_template_props")
        _update_template_prop("base_file_path")
        _update_template_prop("config_path")
        _update_template_prop("config_path_format")

        # Update the tail part of file name to let it could find the dividing configuration
        old_config_file_tail = self.config_file_tail
        self.config_file_tail = (self.config_path_format or self._template_setting.config_path_format).replace("**", "")
        self.config_path = self.config_path.replace(old_config_file_tail, self.config_file_tail)

        if self.apply_template_props:
            data = self._get_dividing_config(data)
        return self

    def _get_dividing_config(self, data: dict) -> dict:
        base_file_path = (
            self.base_file_path or self._current_template.values.base_file_path or self._default_base_file_path
        )
        dividing_config_path = str(pathlib.Path(base_file_path, self.config_path))
        if dividing_config_path and os.path.exists(dividing_config_path) and os.path.isfile(dividing_config_path):
            dividing_data = self._configuration.read(dividing_config_path)
            data.update(**dividing_data)
        return data

    @property
    @abstractmethod
    def _template_setting(self) -> TemplateSetting:
        pass

    def _deserialize_as(
        self, data_model: Type["_TemplatableConfig"], with_data: dict
    ) -> Optional["_TemplatableConfig"]:
        if with_data:
            config = data_model(_current_template=self._current_template)
            config.base_file_path = self.base_file_path
            config.config_path = self.config_path.replace(self.config_file_tail, config.config_file_tail)
            config.absolute_model_key = self.key
            return config.deserialize(data=with_data)
        else:
            return None
