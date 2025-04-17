import inspect
import os
from typing import Optional, Any, get_origin, get_args, Union, List, Dict
from fastapi import HTTPException

from .models import Parameter


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


def resolve_array_items(hint: Any) -> Parameter.ArrayItems:
    origin = get_origin(hint)
    args = get_args(hint)

    if origin in {list, tuple} and args:
        inner = args[0]
        json_type = type_mapping[inner]
        if get_origin(json_type) in {list, tuple}:
            return Parameter.ArrayItems(
                type="array",
                items=resolve_array_items(inner),
            )
        return Parameter.ArrayItems(type=json_type)
    else:
        return Parameter.ArrayItems(type=type_mapping[hint])


def python_type_to_parameters(hint: Any, default: Any = inspect.Parameter.empty) -> Any:
    """
    This method takes in parameter information and transforms it into a Parameter instance.
    Supports nested parameter types as well
    """
    origin = get_origin(hint)
    args = get_args(hint)

    required = default is inspect.Parameter.empty

    # Handle Union types or Optionals (Optional[str] == Union[str, None])
    if origin is Union and type(None) in args:
        required = False
        # Remove NoneType from the args
        args = [arg for arg in args if arg is not type(None)]
        hint = args[0] if args else Any

    # Handle arrays
    if origin in {list, tuple}:
        return Parameter(
            type="array",
            required=required,
            items=resolve_array_items(hint)
        )

    # Handle base types
    return Parameter(
        type=type_mapping[hint],
        required=required,
    )