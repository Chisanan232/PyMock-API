import re
from abc import ABCMeta, abstractmethod
from typing import List, Type, Union

import pytest

from pymock_api.model.enums import ResponseStrategy
from pymock_api.model.openapi._schema_parser import (
    OpenAPIV2SchemaParser,
    OpenAPIV3SchemaParser,
)
from pymock_api.model.openapi._tmp_data_model import (
    BaseTmpDataModel,
    BaseTmpRefDataModel,
    PropertyDetail,
    ResponseProperty,
    TmpConfigReferenceModel,
    TmpReferenceConfigPropertyModel,
    set_component_definition,
)

from ...model.openapi._test_case import DeserializeV2OpenAPIConfigTestCaseFactory

DeserializeV2OpenAPIConfigTestCaseFactory.load()
DESERIALIZE_V2_OPENAPI_DOC_TEST_CASE = DeserializeV2OpenAPIConfigTestCaseFactory.get_test_case()
GENERATE_RESPONSE_CONFIG_FROM_V2_OPENAPI_CONFIG_TEST_CASE = DESERIALIZE_V2_OPENAPI_DOC_TEST_CASE.each_api_http_response


class BaseTmpDataModelTestSuite(metaclass=ABCMeta):

    @pytest.fixture(scope="function")
    @abstractmethod
    def under_test(self) -> BaseTmpDataModel:
        pass

    @pytest.mark.parametrize(
        ("api_response_detail", "entire_config"), GENERATE_RESPONSE_CONFIG_FROM_V2_OPENAPI_CONFIG_TEST_CASE
    )
    def test_generate_response(
        self,
        under_test: BaseTmpRefDataModel,
        api_response_detail: TmpReferenceConfigPropertyModel,
        entire_config: dict,
    ):
        # Pre-process
        set_component_definition(OpenAPIV2SchemaParser(data=entire_config))

        # Run target function under test
        response_prop_data = under_test._generate_response(
            init_response=ResponseProperty(),
            property_value=api_response_detail,
        )

        # Verify
        assert response_prop_data and isinstance(response_prop_data, PropertyDetail)
        # for resp_k, resp_v in response_prop_data.items():
        #     assert resp_k in ["name", "required", "type", "format", "items", "FIXME"]
        # else:
        #     assert response_prop_data and isinstance(response_prop_data, (str, list))
        #     if response_prop_data and isinstance(response_prop_data, str):
        #         assert response_prop_data in [
        #             "random string value",
        #             "random integer value",
        #             "random boolean value",
        #             "random file output stream",
        #             "FIXME: Handle the reference",
        #         ]
        #     else:
        #         for item in response_prop_data:
        #             for item_value in item.values():
        #                 assert item_value in ["random string value", "random integer value", "random boolean value"]

    @pytest.mark.parametrize(
        ("test_response_data", "expected_value"),
        [
            # # # General data
            # For object strategy
            (
                # 1
                {"type": "integer"},
                {"name": "", "required": True, "type": "int"},
            ),
            (
                # 2
                {"type": "number"},
                {"name": "", "required": True, "type": "int"},
            ),
            (
                # 3
                {"type": "boolean"},
                {"name": "", "required": True, "type": "bool"},
            ),
            (
                # 4
                {"type": "array", "items": {"type": "integer"}},
                {
                    "name": "",
                    "required": True,
                    "type": "list",
                    # "format": None,
                    "items": [{"name": "", "required": True, "type": "int"}],
                },
            ),
            (
                # 5
                {"type": "array", "items": {"$ref": "#/components/schemas/FooResponse"}},
                {
                    "name": "",
                    "required": True,
                    "type": "list",
                    # "format": None,
                    "items": [
                        {"name": "id", "required": True, "type": "int"},
                        {"name": "name", "required": True, "type": "str"},
                        {"name": "value1", "required": True, "type": "str"},
                        {"name": "value2", "required": True, "type": "str"},
                    ],
                },
            ),
            (
                # 6
                {"type": "file"},
                {"name": "", "required": True, "type": "file"},
            ),
            # # Special data
            (
                # 7
                {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                    },
                },
                {
                    "name": "",
                    "required": True,
                    "type": "dict",
                    # "format": None,
                    "items": [{"name": "additionalKey", "required": True, "type": "str"}],
                },
            ),
            (
                # 8
                {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["TYPE_1", "TYPE_2"]},
                    },
                },
                {
                    "name": "",
                    "required": True,
                    "type": "list",
                    # "format": None,
                    "items": [
                        {"name": "", "required": True, "type": "str"},
                    ],
                },
            ),
            (
                # 9
                {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": "#/components/schemas/FooResponse",
                    },
                },
                {
                    "name": "additionalKey",
                    "required": True,
                    "type": "dict",
                    # "format": None,
                    "items": [
                        {"name": "id", "required": True, "type": "int"},
                        {"name": "name", "required": False, "type": "str"},
                        {"name": "value1", "required": False, "type": "str"},
                        {"name": "value2", "required": False, "type": "str"},
                    ],
                },
            ),
            (
                # 10
                {
                    "type": "object",
                    "additionalProperties": {
                        "$ref": "#/components/schemas/NestedFooResponse",
                    },
                },
                {
                    "name": "additionalKey",
                    "required": True,
                    "type": "dict",
                    # "format": None,
                    "items": [
                        {"name": "id", "required": True, "type": "int"},
                        {"name": "name", "required": False, "type": "str"},
                        {
                            "name": "data",
                            "required": False,
                            # "format": None,
                            "type": "list",
                            "items": [
                                {"name": "id", "required": True, "type": "int"},
                                {"name": "value", "required": True, "type": "str"},
                                {"name": "url", "required": True, "type": "str"},
                                {
                                    "name": "urlProperties",
                                    "required": False,
                                    # "format": None,
                                    "type": "dict",
                                    "items": [
                                        {
                                            "name": "homePage",
                                            "required": True,
                                            "type": "dict",
                                            # "format": None,
                                            "items": [
                                                {"name": "domain", "required": True, "type": "str"},
                                                {"name": "needAuth", "required": True, "type": "bool"},
                                            ],
                                        },
                                        {
                                            "name": "detailInfo",
                                            "required": True,
                                            "type": "dict",
                                            # "format": None,
                                            "items": [
                                                {"name": "domain", "required": True, "type": "str"},
                                                {"name": "needAuth", "required": True, "type": "bool"},
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ),
            (
                # 11
                {
                    "$ref": "#/components/schemas/NestedFooResponse",
                },
                [
                    {"name": "id", "required": True, "type": "int"},
                    {"name": "name", "required": False, "type": "str"},
                    {
                        "name": "data",
                        "required": False,
                        # "format": None,
                        "type": "list",
                        "items": [
                            {"name": "id", "required": True, "type": "int"},
                            {"name": "value", "required": True, "type": "str"},
                            {"name": "url", "required": True, "type": "str"},
                            {
                                "name": "urlProperties",
                                "required": False,
                                # "format": None,
                                "type": "dict",
                                "items": [
                                    {
                                        "name": "homePage",
                                        "required": True,
                                        "type": "dict",
                                        # "format": None,
                                        "items": [
                                            {"name": "domain", "required": True, "type": "str"},
                                            {"name": "needAuth", "required": True, "type": "bool"},
                                        ],
                                    },
                                    {
                                        "name": "detailInfo",
                                        "required": True,
                                        "type": "dict",
                                        # "format": None,
                                        "items": [
                                            {"name": "domain", "required": True, "type": "str"},
                                            {"name": "needAuth", "required": True, "type": "bool"},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            ),
        ],
    )
    def test_generate_response_from_data(
        self, under_test: BaseTmpRefDataModel, test_response_data: dict, expected_value: str
    ):
        # Pre-process
        if test_response_data.get("type", "array") == "array":
            set_component_definition(
                OpenAPIV3SchemaParser(
                    data={
                        "components": {
                            "schemas": {
                                # For general test
                                "FooResponse": {
                                    "type": "object",
                                    "required": ["id"],
                                    "properties": {
                                        "id": {"type": "integer", "format": "int64"},
                                        "name": {"type": "string"},
                                        "value1": {"type": "string"},
                                        "value2": {"type": "string"},
                                    },
                                    "title": "FooResponse",
                                },
                                # For special case test about nested detail data
                                "NestedFooResponse": {
                                    "type": "object",
                                    "required": ["id"],
                                    "properties": {
                                        "id": {"type": "integer", "format": "int64"},
                                        "name": {"type": "string"},
                                        "data": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/FooDetailResponse"},
                                        },
                                    },
                                },
                                "FooDetailResponse": {
                                    "type": "object",
                                    "required": ["id"],
                                    "properties": {
                                        "id": {"type": "integer", "format": "int64"},
                                        "value": {"type": "string"},
                                        "url": {"type": "string", "format": "uri"},
                                        "urlProperties": {"$ref": "#/components/schemas/UrlProperties"},
                                    },
                                },
                                "UrlProperties": {
                                    "type": "object",
                                    "required": ["homePage", "detailInfo"],
                                    "properties": {
                                        "homePage": {"$ref": "#/components/schemas/DomainProperty"},
                                        "detailInfo": {"$ref": "#/components/schemas/DomainProperty"},
                                    },
                                },
                                "DomainProperty": {
                                    "type": "object",
                                    "required": ["homePage", "needAuth"],
                                    "properties": {
                                        "domain": {"type": "string"},
                                        "needAuth": {"type": "boolean"},
                                    },
                                },
                            },
                        },
                    }
                )
            )
        test_response_data_model = TmpReferenceConfigPropertyModel.deserialize(test_response_data)

        # Run target
        resp = under_test._generate_response_from_data(
            init_response=ResponseProperty.initial_response_data(),
            resp_prop_data=test_response_data_model,
        )

        # Verify
        print(f"resp: {resp}")
        assert resp
        if isinstance(resp, list):
            resp = [r.serialize() for r in resp]
        else:
            resp = resp.serialize()
        assert resp == expected_value


class BaseTmpRefDataModelTestSuite(BaseTmpDataModelTestSuite):

    @pytest.fixture(scope="function")
    @abstractmethod
    def under_test(self) -> BaseTmpRefDataModel:
        pass

    @pytest.mark.parametrize(("under_test", "expect_result"), [])
    @abstractmethod
    def test_has_ref(self, under_test: BaseTmpRefDataModel, expect_result: str):
        assert under_test.has_ref() == expect_result

    @pytest.mark.parametrize(("under_test", "expect_result"), [])
    @abstractmethod
    def test_get_ref(self, under_test: BaseTmpRefDataModel, expect_result: str):
        assert under_test.get_ref() == expect_result

    def test_get_schema_ref_with_not_exist_ref(self, under_test: BaseTmpRefDataModel):
        with pytest.raises(ValueError) as exc_info:
            under_test.get_schema_ref()
        assert re.search(r"no ref", str(exc_info.value), re.IGNORECASE)

    @pytest.mark.parametrize(
        ("ut_response_config", "expect_result"),
        [
            (
                [PropertyDetail(name="THIS_IS_EMPTY", required=True, value_type=None, format=None, items=None)],
                [PropertyDetail(name="", required=True, value_type=None, format=None, is_empty=True, items=None)],
            ),
            (
                [
                    PropertyDetail(
                        name="sample_list",
                        required=True,
                        value_type="list",
                        format=None,
                        items=[
                            PropertyDetail(
                                name="THIS_IS_EMPTY",
                                required=True,
                                value_type=None,
                                format=None,
                                items=None,
                            ),
                        ],
                    ),
                ],
                [
                    PropertyDetail(
                        name="sample_list",
                        required=True,
                        value_type="list",
                        format=None,
                        is_empty=True,
                        items=[],
                    ),
                ],
            ),
            (
                [
                    PropertyDetail(
                        name="sample_list",
                        required=True,
                        value_type="list",
                        format=None,
                        items=[
                            PropertyDetail(
                                name="sample_nested_list",
                                required=True,
                                value_type="list",
                                format=None,
                                items=[
                                    PropertyDetail(
                                        name="sample_nested_list",
                                        required=True,
                                        value_type="list",
                                        format=None,
                                        items=[
                                            PropertyDetail(
                                                name="", required=True, value_type="str", format=None, items=None
                                            ),
                                        ],
                                    ),
                                    PropertyDetail(
                                        name="sample_nested_dict",
                                        required=True,
                                        value_type="dict",
                                        format=None,
                                        items=[
                                            PropertyDetail(
                                                name="THIS_IS_EMPTY",
                                                required=True,
                                                value_type=None,
                                                format=None,
                                                items=None,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
                [
                    PropertyDetail(
                        name="sample_list",
                        required=True,
                        value_type="list",
                        format=None,
                        items=[
                            PropertyDetail(
                                name="sample_nested_list",
                                required=True,
                                value_type="list",
                                format=None,
                                items=[
                                    PropertyDetail(
                                        name="sample_nested_list",
                                        required=True,
                                        value_type="list",
                                        format=None,
                                        items=[
                                            PropertyDetail(
                                                name="", required=True, value_type="str", format=None, items=None
                                            ),
                                        ],
                                    ),
                                    PropertyDetail(
                                        name="sample_nested_dict",
                                        required=True,
                                        value_type="dict",
                                        format=None,
                                        is_empty=True,
                                        items=[],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    def test__process_empty_body_response(
        self,
        under_test: BaseTmpRefDataModel,
        ut_response_config: List[PropertyDetail],
        expect_result: List[PropertyDetail],
    ):
        new_response_config = under_test._process_empty_body_response(response_columns_setting=ut_response_config)
        assert new_response_config == expect_result


class TestTmpResponsePropertyModel(BaseTmpRefDataModelTestSuite):

    @pytest.fixture(scope="function")
    def under_test(self) -> TmpReferenceConfigPropertyModel:
        return TmpReferenceConfigPropertyModel()

    @pytest.mark.parametrize(
        ("under_test", "expect_result"),
        [
            (TmpReferenceConfigPropertyModel(ref=None), ""),
            (TmpReferenceConfigPropertyModel(ref=""), ""),
            (TmpReferenceConfigPropertyModel(ref="reference value"), "ref"),
            (TmpReferenceConfigPropertyModel(additionalProperties=TmpReferenceConfigPropertyModel(ref=None)), ""),
            (TmpReferenceConfigPropertyModel(additionalProperties=TmpReferenceConfigPropertyModel(ref="")), ""),
            (
                TmpReferenceConfigPropertyModel(
                    additionalProperties=TmpReferenceConfigPropertyModel(ref="reference value")
                ),
                "additionalProperties",
            ),
        ],
    )
    def test_has_ref(self, under_test: BaseTmpRefDataModel, expect_result: str):
        super().test_has_ref(under_test, expect_result)

    @pytest.mark.parametrize(
        ("under_test", "expect_result"),
        [
            (TmpReferenceConfigPropertyModel(ref="reference value"), "reference value"),
            (
                TmpReferenceConfigPropertyModel(
                    additionalProperties=TmpReferenceConfigPropertyModel(ref="reference value")
                ),
                "reference value",
            ),
        ],
    )
    def test_get_ref(self, under_test: BaseTmpRefDataModel, expect_result: str):
        super().test_get_ref(under_test, expect_result)

    @pytest.mark.parametrize(
        ("under_test", "expect_result"),
        [
            (TmpReferenceConfigPropertyModel(), True),
            (TmpReferenceConfigPropertyModel(value_type=None), True),
            (TmpReferenceConfigPropertyModel(ref=None), True),
            (TmpReferenceConfigPropertyModel(value_type=""), True),
            (TmpReferenceConfigPropertyModel(ref=""), True),
            (TmpReferenceConfigPropertyModel(value_type="data type", ref=""), False),
            (TmpReferenceConfigPropertyModel(value_type=None, ref="reference value"), False),
        ],
    )
    def test_is_empty(self, under_test: TmpReferenceConfigPropertyModel, expect_result: str):
        assert under_test.is_empty() == expect_result


class TestTmpResponseRefModel(BaseTmpDataModelTestSuite):

    @pytest.fixture(scope="function")
    def under_test(self) -> TmpConfigReferenceModel:
        return TmpConfigReferenceModel()

    @pytest.mark.parametrize(
        ("strategy", "test_response_data", "expected_value"),
        [
            # (
            #     ResponseStrategy.STRING,
            #     {"type": "object"},
            #     {"strategy": ResponseStrategy.STRING, "data": {"THIS_IS_EMPTY": "empty value"}},
            # ),
            (
                ResponseStrategy.OBJECT,
                TmpConfigReferenceModel(value_type="object"),
                # {"type": "object"},
                ResponseProperty(
                    data=[PropertyDetail(name="THIS_IS_EMPTY", required=False, value_type=None, format=None, items=[])],
                ),
                # {
                #     "strategy": ResponseStrategy.OBJECT,
                #     "data": [{"name": "THIS_IS_EMPTY", "required": False, "type": None, "format": None, "items": []}],
                # },
            ),
        ],
    )
    def test__process_reference_object_with_empty_body_response(
        self, strategy: ResponseStrategy, test_response_data: TmpConfigReferenceModel, expected_value: ResponseProperty
    ):
        response_config = test_response_data.process_reference_object(
            init_response=ResponseProperty.initial_response_data(),
        )
        assert response_config == expected_value


class TestPropertyDetail:

    @pytest.mark.parametrize(
        ("strategy", "expected_type"),
        [
            (ResponseStrategy.OBJECT, PropertyDetail),
        ],
    )
    def test_generate_empty_response(self, strategy: ResponseStrategy, expected_type: Union[type, Type]):
        empty_resp = PropertyDetail.generate_empty_response()
        assert isinstance(empty_resp, expected_type)