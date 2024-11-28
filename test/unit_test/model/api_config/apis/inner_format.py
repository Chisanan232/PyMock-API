import re
from typing import Any, List

import pytest

from pymock_api.model.api_config.apis._format import Format
from pymock_api.model.api_config.variable import Variable
from pymock_api.model.enums import FormatStrategy

from ....._values import _Customize_Format_With_Self_Vars
from .._base import CheckableTestSuite, _assertion_msg, set_checking_test_data


class TestFormat(CheckableTestSuite):
    test_data_dir = "format"
    set_checking_test_data(test_data_dir)

    @pytest.fixture(scope="function")
    def sut(self) -> Format:
        return Format(
            strategy=_Customize_Format_With_Self_Vars["strategy"],
            enums=_Customize_Format_With_Self_Vars["enums"],
            customize=_Customize_Format_With_Self_Vars["customize"],
            variables=_Customize_Format_With_Self_Vars["variables"],
        )

    @pytest.fixture(scope="function")
    def sut_with_nothing(self) -> Format:
        return Format()

    def test_value_attributes(self, sut: Format):
        self._verify_props_value(sut)

    def _expected_serialize_value(self) -> Any:
        return _Customize_Format_With_Self_Vars

    def _expected_deserialize_value(self, obj: Format) -> None:
        assert isinstance(obj, Format)
        self._verify_props_value(ut_obj=obj)

    def _verify_props_value(self, ut_obj: Format) -> None:
        assert ut_obj.strategy.value == _Customize_Format_With_Self_Vars["strategy"], _assertion_msg
        assert ut_obj.enums is _Customize_Format_With_Self_Vars["enums"], _assertion_msg
        assert ut_obj.customize is _Customize_Format_With_Self_Vars["customize"], _assertion_msg
        for var in ut_obj.variables:
            expect_var_value = list(
                filter(lambda v: v["name"] == var.name, _Customize_Format_With_Self_Vars["variables"])
            )
            assert expect_var_value and len(expect_var_value) == 1
            assert var.name == expect_var_value[0]["name"]
            assert var.value_format.value == expect_var_value[0]["value_format"]
            assert var.value == expect_var_value[0]["value"]
            assert var.range == expect_var_value[0]["range"]
            assert var.enum == expect_var_value[0]["enum"]

    @pytest.mark.parametrize("invalid_data", ["invalid data type", ["invalid data type"]])
    def test_invalid_data_at_prop_variables(self, invalid_data: Any):
        with pytest.raises(TypeError) as exc_info:
            Format(variables=invalid_data)
        assert re.search(
            r".{0,32}data type(.,*){0,32}variables(.,*){0,32}be(.,'){0,32}", str(exc_info.value), re.IGNORECASE
        )

    def test_set_with_invalid_value(self, sut_with_nothing: Format):
        with pytest.raises(ValueError) as exc_info:
            sut_with_nothing.deserialize(data={"strategy": None})
        assert re.search(r"(.,*){0,32}strategy(.,*){0,32}cannot be empty", str(exc_info.value), re.IGNORECASE)

    @pytest.mark.parametrize(
        ("ut_obj", "other_obj"),
        [
            (Format(strategy=FormatStrategy.RANDOM_STRING), Format(strategy=FormatStrategy.CUSTOMIZE)),
            (
                Format(strategy=FormatStrategy.FROM_ENUMS, enums=["ENUM_1", "ENUM_2"]),
                Format(strategy=FormatStrategy.FROM_ENUMS, enums=["ENUM_3"]),
            ),
            (
                Format(strategy=FormatStrategy.CUSTOMIZE, customize="sample customize"),
                Format(strategy=FormatStrategy.CUSTOMIZE, customize="different customize"),
            ),
            (
                Format(
                    strategy=FormatStrategy.CUSTOMIZE,
                    customize="customize with var",
                    variables=[Variable(name="sample var")],
                ),
                Format(
                    strategy=FormatStrategy.CUSTOMIZE,
                    customize="customize with var",
                    variables=[Variable(name="different var name")],
                ),
            ),
            (
                Format(
                    strategy=FormatStrategy.CUSTOMIZE,
                    customize="customize with var",
                    variables=[Variable(name="sample var", value="20")],
                ),
                Format(
                    strategy=FormatStrategy.CUSTOMIZE,
                    customize="customize with var",
                    variables=[Variable(name="sample var", value="30:2")],
                ),
            ),
        ],
    )
    def test_compare(self, ut_obj: Format, other_obj: Format):
        assert ut_obj != other_obj

    @pytest.mark.parametrize(
        ("strategy", "value", "enums", "customize"),
        [
            (FormatStrategy.RANDOM_STRING, "random_string", [], ""),
            (FormatStrategy.RANDOM_INTEGER, 123, [], ""),
            (FormatStrategy.RANDOM_BIG_DECIMAL, 123.123, [], ""),
            (FormatStrategy.RANDOM_BOOLEAN, True, [], ""),
            (FormatStrategy.RANDOM_BOOLEAN, False, [], ""),
            (FormatStrategy.FROM_ENUMS, "ENUM_2", ["ENUM_1", "ENUM_2", "ENUM_3"], ""),
            (FormatStrategy.CUSTOMIZE, "sample_format", [], "sample_format"),
        ],
    )
    def test_chk_format_is_match(self, strategy: FormatStrategy, value: Any, enums: List[str], customize: str):
        format_model = Format(strategy=strategy, enums=enums, customize=customize)
        assert format_model.value_format_is_match(value=value, enums=enums, customize=customize) is True

    @pytest.mark.parametrize(
        ("strategy", "value", "enums", "customize"),
        [
            (FormatStrategy.RANDOM_STRING, 123, [], ""),
            (FormatStrategy.RANDOM_INTEGER, "not int value", [], ""),
            (FormatStrategy.RANDOM_BIG_DECIMAL, "not int or float value", [], ""),
            (FormatStrategy.RANDOM_BOOLEAN, "not bool value", [], ""),
            (FormatStrategy.RANDOM_BOOLEAN, "False", [], ""),
            (FormatStrategy.FROM_ENUMS, "not in enums", ["ENUM_1", "ENUM_2", "ENUM_3"], ""),
            (FormatStrategy.CUSTOMIZE, "different_format", [], "sample_format"),
        ],
    )
    def test_failure_chk_format_is_match(self, strategy: FormatStrategy, value: Any, enums: List[str], customize: str):
        format_model = Format(strategy=strategy, enums=enums, customize=customize)
        assert format_model.value_format_is_match(value=value, enums=enums, customize=customize) is False