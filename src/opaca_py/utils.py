import os
from typing import Optional, Any, get_origin, get_args, Union, List, Dict
from fastapi import HTTPException


def http_error(code: int, cause: str) -> HTTPException:
    """
    custom http exception like in assessment example solution
    """
    return HTTPException(status_code=code, detail={"cause": cause})


def get_env_var(name: str, default_value: Any = None) -> Optional[str]:
    if name in os.environ:
        return os.environ.get(name)
    return default_value


type_mapping = {
    int: "number",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def python_type_to_json_type(py_type: Any) -> Any:
    origin = get_origin(py_type)
    args = get_args(py_type)

    if py_type in type_mapping:
        return type_mapping[py_type]

    elif origin is Union:
        json_types = [python_type_to_json_type(arg) for arg in args]
        # Remove duplicates
        return list(set(json_types))

    elif origin in (list, List):
        return {
            "type": "array",
            "items": {"type": python_type_to_json_type(args[0]) if args else "object"}
        }

    elif origin in (dict, Dict):
        return {
            "type": "object",
            "additionalProperties": {"type": python_type_to_json_type(args[1]) if args else "object"}
        }

    # Fallback
    return "object"