import copy
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ...._utils import YAML
from ...._utils.file_opt import JSON
from ...enums import Format, ResponseStrategy
from .._base import _Checkable, _Config
from .._divide import _BeDividedable, _Dividable
from ..template import (
    TemplateAPI,
    TemplateConfig,
    TemplateConfigLoadable,
    TemplateConfigLoader,
    TemplateConfigOpts,
    TemplateHTTP,
    _TemplatableConfig,
)
from .request import APIParameter, HTTPRequest
from .response import HTTPResponse, ResponseProperty


@dataclass(eq=False)
class HTTP(_TemplatableConfig, TemplateConfigOpts, _Checkable, _BeDividedable, _Dividable):
    """*The **http** section in **mocked_apis.<api>***"""

    config_file_tail: str = "-http"

    request: Optional[HTTPRequest] = None
    response: Optional[HTTPResponse] = None

    _request: Optional[HTTPRequest] = field(init=False, repr=False)
    _response: Optional[HTTPResponse] = field(init=False, repr=False)

    _current_section: str = ""
    _template_config_loader: Optional[TemplateConfigLoadable] = None

    def __post_init__(self):
        if self._template_config_loader is None:
            self._template_config_loader = TemplateConfigLoader()
            self._template_config_loader.register(self.register_callbacks())

    def _compare(self, other: "HTTP") -> bool:
        templatable_config = super()._compare(other)
        return templatable_config and self.request == other.request and self.response == other.response

    @property
    def key(self) -> str:
        return "http"

    @property  # type: ignore[no-redef]
    def request(self) -> Optional[HTTPRequest]:
        return self._request

    @request.setter
    def request(self, req: Union[dict, HTTPRequest]) -> None:
        if req is not None:
            if isinstance(req, dict):
                self._request = HTTPRequest().deserialize(data=req)
            elif isinstance(req, HTTPRequest):
                self._request = req
            elif isinstance(req, property):
                # For initialing
                self._request = None
            else:
                raise TypeError("Setter *HTTP.request* only accepts dict or HTTPRequest type object.")

    @property  # type: ignore[no-redef]
    def response(self) -> Optional[HTTPResponse]:
        return self._response

    @response.setter
    def response(self, resp: Union[dict, HTTPResponse]) -> None:
        if resp is not None:
            if isinstance(resp, dict):
                self._response = HTTPResponse().deserialize(data=resp)
            elif isinstance(resp, HTTPResponse):
                self._response = resp
            elif isinstance(resp, property):
                # For initialing
                self._response = None
            else:
                raise TypeError("Setter *HTTP.response* only accepts dict or HTTPResponse type object.")

    @property
    def should_divide(self) -> bool:
        if self._current_section.lower() == "request":
            return self._divide_strategy.divide_http_request
        if self._current_section.lower() == "response":
            return self._divide_strategy.divide_http_response
        raise ValueError("Inner property *HTTP._current_section* value must to be *request* or *response*.")

    def serialize(self, data: Optional["HTTP"] = None) -> Optional[Dict[str, Any]]:
        req = (data or self).request if (data and data.request) or self.request else None
        resp = (data or self).response if (data and data.response) or self.response else None
        if not (req and resp):
            return None

        serialized_data = super().serialize(data)
        assert serialized_data is not None

        # Set HTTP request and HTTP response data modal
        self._process_dividing_serialize_http_props(
            init_data=serialized_data,
            data_modal=req,
            key="request",
            should_set_dividable_value_callback=lambda: self.should_set_bedividedable_value
            and not self._divide_strategy.divide_http_request,
        )
        self._process_dividing_serialize_http_props(
            init_data=serialized_data,
            data_modal=resp,
            key="response",
            should_set_dividable_value_callback=lambda: self.should_set_bedividedable_value
            and not self._divide_strategy.divide_http_response,
        )

        return serialized_data

    def _process_dividing_serialize_http_props(
        self,
        data_modal: Union[_Config, _BeDividedable, _TemplatableConfig],
        init_data: Dict[str, Any],
        key: str = "",
        should_set_dividable_value_callback: Optional[Callable] = None,
    ) -> None:
        self._current_section = key
        self._process_dividing_serialize(
            init_data=init_data,
            data_modal=data_modal,
            key=key,
            api_name=self.api_name,
            tag=self.tag,
            should_set_dividable_value_callback=should_set_dividable_value_callback,
        )

    @property
    def _current_template_at_serialization(self) -> TemplateConfig:
        return self._current_template

    def _set_serialized_data(
        self, init_data: Dict[str, Any], serialized_data: Optional[Union[str, dict]], key: str = ""
    ) -> None:
        assert key, "Key in configuration cannot be empty."
        init_data.update({key: serialized_data})

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["HTTP"]:
        """Convert data to **HTTP** type object.

        The data structure should be like following:

        * Example data:
        .. code-block:: python

            {
                'http': {
                    'request': {
                        'method': 'GET',
                        'parameters': {'param1': 'val1'}
                    },
                    'response': {
                        'value': 'This is Google home API.'
                    }
                }
            }

        Args:
            data (Dict[str, Any]): Target data to convert.

        Returns:
            A **HTTP** type object.

        """

        super().deserialize(data)

        req = data.get("request", None)
        resp = data.get("response", None)
        self._current_section = "request"
        if req:
            self.request = self._deserialize_as(HTTPRequest, with_data=req)  # type: ignore[assignment]
        else:
            assert self._template_config_loader
            self._template_config_loader._load_templatable_config()
        self._current_section = "response"
        if resp:
            self.response = self._deserialize_as(HTTPResponse, with_data=resp)  # type: ignore[assignment]
        else:
            assert self._template_config_loader
            self._template_config_loader._load_templatable_config()
        self._current_section = "request"
        return self

    @property
    def _template_setting(self) -> TemplateHTTP:
        return self._current_template.values.http

    def is_work(self) -> bool:
        if not self.props_should_not_be_none(
            under_check={
                f"{self.absolute_model_key}.request": self.request,
                f"{self.absolute_model_key}.response": self.response,
            }
        ):
            return False
        assert self.request is not None
        self.request.stop_if_fail = self.stop_if_fail
        assert self.response is not None
        self.response.stop_if_fail = self.stop_if_fail
        return self.request.is_work() and self.response.is_work()

    @property
    def _template_config(self) -> TemplateConfig:
        return self._current_template

    @property
    def _config_file_format(self) -> str:
        if self._current_section.lower() == "request":
            return self._current_template.values.request.config_path_format
        if self._current_section.lower() == "response":
            return self._current_template.values.response.config_path_format
        raise ValueError(
            "Inner property *HTTPRequest._current_section*, *HTTPResponse._current_section* value must to be *request*"
            " or *response*."
        )

    @property
    def _deserialize_as_template_config(self) -> Union[HTTPRequest, HTTPResponse]:
        if self._current_section.lower() == "request":
            http_prop = HTTPRequest(_current_template=self._current_template)
        elif self._current_section.lower() == "response":
            http_prop = HTTPResponse(_current_template=self._current_template)  # type: ignore[assignment]
        else:
            raise ValueError(
                "Inner property *HTTPRequest._current_section*, *HTTPResponse._current_section* value must to be "
                "*request* or *response*."
            )
        http_prop.absolute_model_key = self.key
        return http_prop

    def _set_template_config(self, config: _Config, **kwargs) -> None:
        # Set the data model in config
        if self._current_section.lower() == "request":
            self.request = config  # type: ignore[assignment]
        if self._current_section.lower() == "response":
            self.response = config  # type: ignore[assignment]

    def _set_mocked_apis(self, api_key: str = "", api_config: Optional[_Config] = None) -> None:
        # FIXME: Should not be an abstract method force every data modal to implement it
        pass


@dataclass(eq=False)
class MockAPI(_TemplatableConfig, TemplateConfigOpts, _Checkable, _BeDividedable, _Dividable):
    """*The **<api>** section in **mocked_apis***"""

    config_file_tail: str = "-api"

    url: str = field(default_factory=str)
    http: Optional[HTTP] = None
    tag: str = field(default_factory=str)

    _url: str = field(init=False, repr=False)
    _http: Optional[HTTP] = field(init=False, repr=False)
    _tag: str = field(init=False, repr=False)

    _template_config_loader: Optional[TemplateConfigLoadable] = None

    def __post_init__(self):
        if self._template_config_loader is None:
            self._template_config_loader = TemplateConfigLoader()
            self._template_config_loader.register(self.register_callbacks())

    def _compare(self, other: "MockAPI") -> bool:
        templatable_config = super()._compare(other)
        return templatable_config and self.url == other.url and self.http == other.http

    @property
    def key(self) -> str:
        return "<mock API>"

    @property  # type: ignore[no-redef]
    def url(self) -> Optional[str]:
        return self._url

    @url.setter
    def url(self, url: str) -> None:
        self._url = url

    @property  # type: ignore[no-redef]
    def http(self) -> Optional[HTTP]:
        return self._http

    @http.setter
    def http(self, http: Union[dict, HTTP]) -> None:
        if http is not None:
            if isinstance(http, dict):
                self._http = HTTP().deserialize(data=http)
            elif isinstance(http, HTTP):
                self._http = http
            elif isinstance(http, property):
                # For initialing
                self._http = None
            else:
                raise TypeError(f"Setter *MockAPI.http* only accepts dict or HTTP type object. But it got '{http}'.")
        else:
            self._http = None

    @property  # type: ignore[no-redef]
    def tag(self) -> str:
        return self._tag

    @tag.setter
    def tag(self, tag: str) -> None:
        if isinstance(tag, str):
            self._tag = tag
        elif isinstance(tag, property):
            # For initialing
            self._tag = ""
        else:
            raise TypeError(f"Setter *MockAPI.tag* only accepts str type value. But it got '{tag}'.")

    @property
    def should_divide(self) -> bool:
        return self._divide_strategy.divide_http

    def serialize(self, data: Optional["MockAPI"] = None) -> Optional[Dict[str, Any]]:
        url = (data.url if data else None) or self.url
        http = (data.http if data else None) or self.http
        if not (url and http):
            return None
        tag = (data.tag if data else None) or self.tag
        serialized_data = super().serialize(data)
        assert serialized_data is not None

        # Set HTTP data modal
        updated_data = {
            "url": url,
            "tag": tag,
        }
        self._process_dividing_serialize(
            init_data=updated_data,
            data_modal=http,
            api_name=self.api_name,
            tag=self.tag,
        )
        serialized_data.update(updated_data)

        return serialized_data

    @property
    def _current_template_at_serialization(self) -> TemplateConfig:
        return self._current_template

    def _set_serialized_data(
        self, init_data: Dict[str, Any], serialized_data: Optional[Union[str, dict]], key: str = ""
    ) -> None:
        init_data["http"] = serialized_data

    @_Config._ensure_process_with_not_empty_value
    def deserialize(self, data: Dict[str, Any]) -> Optional["MockAPI"]:
        """Convert data to **MockAPI** type object.

        The data structure should be like following:

        * Example data:
        .. code-block:: python

            {
                <mocked API's name>: {
                    'url': '/google',
                    'http': {
                        'request': {
                            'method': 'GET',
                            'parameters': {'param1': 'val1'}
                        },
                        'response': {
                            'value': 'This is Google home API.'
                        }
                    }
                },
            }

        Args:
            data (Dict[str, Any]): Target data to convert.

        Returns:
            A **MockAPI** type object.

        """

        super().deserialize(data)

        self.url = data.get("url", None)
        http_info = data.get("http", {})
        print(f"[DEBUG in MockAPI.deserialize] http_info: {http_info}")
        if http_info:
            self.http = self._deserialize_as(HTTP, with_data=http_info)  # type: ignore[assignment]
        else:
            assert self._template_config_loader
            self._template_config_loader._load_templatable_config()
        if self.http is not None:
            self.http._current_template = self._current_template
        self.tag = data.get("tag", "")
        return self

    def is_work(self) -> bool:
        if not self.should_not_be_none(
            config_key=f"{self.absolute_model_key}.http",
            config_value=self.http,
        ):
            return False

        if not self.should_not_be_none(
            config_key=f"{self.absolute_model_key}.url",
            config_value=self.url,
            accept_empty=False,
        ):
            return False
        valid_url = re.findall(r"\/[\w,\-,\_]{1,32}", self.url)
        url_copy = copy.copy(self.url)
        if not valid_url:
            return False
        if url_copy.replace("".join(valid_url), ""):
            return False

        assert self.http is not None
        self.http.stop_if_fail = self.stop_if_fail
        return self.http.is_work()

    @property
    def _template_setting(self) -> TemplateAPI:
        return self._current_template.values.api

    def set_request(self, method: str = "GET", parameters: Optional[List[Union[dict, APIParameter]]] = None) -> None:
        def _convert(param: Union[dict, APIParameter]) -> APIParameter:
            if isinstance(param, APIParameter):
                return param
            ap = APIParameter()
            ap_data_obj_fields = list(ap.__dataclass_fields__.keys())
            ap_data_obj_fields.pop(ap_data_obj_fields.index("value_type"))
            ap_data_obj_fields.append("type")
            if False in list(map(lambda p: p in ap_data_obj_fields, param.keys())):
                raise ValueError("The data format of API parameter is incorrect.")
            return ap.deserialize(param)

        if parameters and False in list(map(lambda p: isinstance(p, APIParameter), parameters)):
            params = list(map(_convert, parameters))
        else:
            params = parameters or []  # type: ignore[assignment]
        if not self.http:
            self.http = HTTP(request=HTTPRequest(method=method, parameters=params), response=HTTPResponse())
        else:
            if not self.http.request:
                self.http.request = HTTPRequest(method=method, parameters=params)
            else:
                if method:
                    self.http.request.method = method
                if parameters:
                    self.http.request.parameters = params

    def set_response(
        self, strategy: ResponseStrategy = ResponseStrategy.STRING, value: str = "", iterable_value: List = []
    ) -> None:
        if strategy is ResponseStrategy.STRING:
            http_resp = HTTPResponse(strategy=strategy, value=value)
        elif strategy is ResponseStrategy.FILE:
            http_resp = HTTPResponse(strategy=strategy, path=value)
        elif strategy is ResponseStrategy.OBJECT:
            http_resp = HTTPResponse(strategy=strategy, properties=iterable_value)
        else:
            raise TypeError(f"Invalid response strategy *{strategy}*.")

        if not self.http:
            self.http = HTTP(request=HTTPRequest(), response=http_resp)
        else:
            self.http.response = http_resp

    def format(self, f: Format) -> str:
        def _ensure_getting_serialized_data() -> Dict[str, Any]:
            serialized_data = self.serialize()
            assert serialized_data, "It must have non-empty value for formatting."
            return serialized_data

        if f == Format.JSON:
            return JSON().serialize(_ensure_getting_serialized_data())
        elif f == Format.YAML:
            return YAML().serialize(_ensure_getting_serialized_data())
        else:
            raise ValueError(f"Not support the format feature as {f}.")

    @property
    def _template_config(self) -> TemplateConfig:
        return self._current_template

    @property
    def _config_file_format(self) -> str:
        return self._current_template.values.http.config_path_format

    @property
    def _deserialize_as_template_config(self) -> HTTP:
        http = HTTP(_current_template=self._current_template)
        http.absolute_model_key = self.key
        return http

    def _set_template_config(self, config: _Config, **kwargs) -> None:
        # Set the data model in config
        self.http = config  # type: ignore[assignment]

    def _set_mocked_apis(self, api_key: str = "", api_config: Optional[_Config] = None) -> None:
        # FIXME: Should not be an abstract method force every data modal to implement it
        pass
