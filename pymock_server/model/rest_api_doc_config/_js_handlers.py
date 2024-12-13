from enum import Enum
from typing import Union


def convert_js_type(t: str) -> str:
    if t == "string":
        return "str"
    elif t in ["integer", "number"]:
        return "int"
    elif t == "boolean":
        return "bool"
    elif t == "array":
        return "list"
    elif t == "file":
        return "file"
    elif t == "object":
        return "dict"
    else:
        raise TypeError(f"Currently, it cannot parse JS type '{t}'.")


# TODO: Should clean the parsing process
def ensure_type_is_python_type(t: str) -> str:
    if t in ["string", "integer", "number", "boolean", "array", "object"]:
        return convert_js_type(t)
    return t


class ApiDocValueFormat(Enum):
    DateTime: str = "date-time"
    Int32: str = "int32"
    Int64: str = "int64"
    Float: str = "float"
    Double: str = "double"
    Password: str = "password"

    @staticmethod
    def to_enum(v: Union[str, "ApiDocValueFormat"]) -> "ApiDocValueFormat":
        if isinstance(v, ApiDocValueFormat):
            return v
        for formatter in ApiDocValueFormat:
            if formatter.value.lower() == v.lower():
                return formatter
        raise ValueError(f"Cannot map anyone format with value '{v}'.")
