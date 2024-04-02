import re
from typing import Type
from unittest.mock import patch

import pytest

from pymock_api.model.enums import OpenAPIVersion
from pymock_api.model.openapi._parser_factory import (
    BaseOpenAPIParserFactory,
    OpenAPIParserFactory,
    get_parser_factory,
)


@pytest.mark.parametrize(
    ("openapi_version", "expected_factory"),
    [
        # Enum type
        (OpenAPIVersion.V2, OpenAPIParserFactory),
        (OpenAPIVersion.V3, OpenAPIParserFactory),
        # str type
        ("2.0.0", OpenAPIParserFactory),
        ("2.4.8", OpenAPIParserFactory),
        ("3.0.0", OpenAPIParserFactory),
        ("3.1.0", OpenAPIParserFactory),
    ],
)
def test_get_parser_factory(openapi_version: OpenAPIVersion, expected_factory: Type[BaseOpenAPIParserFactory]):
    factory = get_parser_factory(version=openapi_version)
    isinstance(factory, expected_factory)


@pytest.mark.parametrize(
    ("openapi_version", "expected_factory"),
    [
        ("4.0.0", OpenAPIParserFactory),
        ("invalid version", OpenAPIParserFactory),
    ],
)
def test_get_parser_factory_with_invalid_version(
    openapi_version: OpenAPIVersion, expected_factory: Type[BaseOpenAPIParserFactory]
):
    with patch("pymock_api.model.openapi._parser_factory.OpenAPIVersion.to_enum", return_value=openapi_version):
        with pytest.raises(NotImplementedError) as exc_info:
            get_parser_factory(version=openapi_version)
        re.search(re.escape(openapi_version), str(exc_info.value), re.IGNORECASE)