import json
import os
import re
from typing import Dict, List, Type

import pytest

from pymock_api.model.openapi._schema_parser import (
    BaseOpenAPISchemaParser,
    OpenAPIV2SchemaParser,
    OpenAPIV3SchemaParser,
)


class DummyOpenAPISchemaParser(BaseOpenAPISchemaParser):
    def get_paths(self) -> Dict[str, Dict]:
        return {}

    def get_tags(self) -> List[dict]:
        return []

    def get_objects(self) -> Dict[str, dict]:
        return {}


class TestOpenAPIParser:

    @pytest.fixture(scope="function")
    def parser(self) -> Type[BaseOpenAPISchemaParser]:
        return DummyOpenAPISchemaParser

    @pytest.mark.parametrize("impl_parser", [OpenAPIV2SchemaParser, OpenAPIV3SchemaParser])
    def test_initial_parser_with_valid_file(self, impl_parser: Type[BaseOpenAPISchemaParser]):
        file_path: str = "./test.json"
        try:
            # Given
            with open(file_path, "a+", encoding="utf-8") as io_stream:
                io_stream.write(json.dumps({"paths": "test API"}))

            # Run target function
            parser_instance = impl_parser(file=file_path)

            # Verify
            assert parser_instance.get_paths() == "test API"
        finally:
            os.remove(file_path)

    def test_initial_parser_with_invalid_file(self, parser: Type[BaseOpenAPISchemaParser]):
        # Run target function
        with pytest.raises(FileNotFoundError) as exc_info:
            DummyOpenAPISchemaParser(file="./not_exist.json")

        # Verify
        assert re.search(r".{0,32}not find.{0,32}OpenAPI format configuration", str(exc_info.value), re.IGNORECASE)
