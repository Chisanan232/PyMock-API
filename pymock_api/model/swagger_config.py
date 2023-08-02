import json
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Type

from pymock_api.model.api_config import APIConfig
from pymock_api.model.api_config import APIParameter as PyMockAPIParameter
from pymock_api.model.api_config import BaseConfig, MockAPI, MockAPIs, _Config

Self = Any


def convert_js_type(t: str) -> str:
    if t == "string":
        return "str"
    elif t == "integer":
        return "int"
    elif t == "boolean":
        return "bool"
    else:
        raise TypeError(f"Currently, it cannot parse JS type '{t}'.")


class BaseSwaggerDataModel(metaclass=ABCMeta):
    @abstractmethod
    def deserialize(self, data: Dict) -> Self:
        pass

    @abstractmethod
    def to_api_config(self) -> _Config:
        pass


class APIParameter(BaseSwaggerDataModel):
    def __init__(self):
        self.name: str = ""
        self.required: bool = False
        self.value_type: str = ""
        self.default: Any = None

    def deserialize(self, data: Dict) -> "APIParameter":
        self.name = data["name"]
        self.required = data["required"]
        self.value_type = convert_js_type(data["schema"]["type"])
        self.default = data["schema"]["default"]
        return self

    def to_api_config(self) -> PyMockAPIParameter:
        return PyMockAPIParameter(
            name=self.name,
            required=self.required,
            value_type=self.value_type,
            default=self.default,
            value_format="",
        )


class API(BaseSwaggerDataModel):
    def __init__(self):
        self.path: str = ""
        self.http_method: str = ""
        self.parameters: List[APIParameter] = []
        self.response: Dict = {}

    def deserialize(self, data: Dict) -> "API":
        for http_method, http_info in data.items():
            self.http_method = http_method
            self.parameters = list(map(lambda p: APIParameter().deserialize(data=p), http_info["parameters"]))
            # TODO: Process the response
            self.response = http_info["responses"]
        return self

    def to_api_config(self) -> MockAPI:
        mock_api = MockAPI(url=self.path)
        mock_api.set_request(
            method=self.http_method,
            parameters=list(map(lambda p: p.to_api_config(), self.parameters)),
        )
        mock_api.set_response(value=json.dumps(self.response))
        return mock_api


class SwaggerConfig(BaseSwaggerDataModel):
    def __init__(self):
        self.paths: List[API] = []

    def deserialize(self, data: Dict) -> "SwaggerConfig":
        apis: dict = data["paths"]
        for api_path, api_props in apis.items():
            api = API().deserialize(data=api_props)
            api.path = api_path
            self.paths.append(api)
        return self

    def to_api_config(self) -> APIConfig:
        api_config = APIConfig(name="", description="", apis=MockAPIs(base=BaseConfig(url=""), apis={}))
        assert api_config.apis is not None and api_config.apis.apis == {}
        for swagger_api in self.paths:
            api_config.apis.apis[swagger_api.path] = swagger_api.to_api_config()
        return api_config
