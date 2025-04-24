import inspect
import os
from typing import Optional, Any, get_origin, get_args, Union
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
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def resolve_array_items(hint: Any) -> Parameter.ArrayItems:
    """
    Recursive function to resolve array items.
    """
    origin = get_origin(hint)
    args = get_args(hint)

    if origin in {list, tuple} and args:
        inner = args[0]
        if inspect.isclass(inner):
            return Parameter.ArrayItems(
                type=inner.__name__,
            )
        if get_origin(inner) in {list, tuple}:
            return Parameter.ArrayItems(
                type="array",
                items=resolve_array_items(inner),
            )
        return Parameter.ArrayItems(type=type_mapping[inner])
    else:
        return Parameter.ArrayItems(type=type_mapping[hint])


def python_type_to_parameter(hint: Any, default: Any = inspect.Parameter.empty) -> Any:
    """
    This method takes in parameter information and transforms it into a Parameter instance.
    Supports nested parameter types and custom objects.
    """
    origin = get_origin(hint)
    args = get_args(hint)

    required = default is inspect.Parameter.empty

    # Handle Union types with none or Optionals (Optional[str] == Union[str, None])
    if origin is Union and type(None) in args:
        required = False
        # Remove NoneType from the args
        args = [arg for arg in args if arg is not type(None)]
        hint = args[0] if args else Any

    # Use the custom object name if the hint is a class, otherwise use standard type names
    if inspect.isclass(hint):
        _type = hint.__name__
    else:
        _type = type_mapping[origin]

    # Handle base types
    return Parameter(
        type=_type,
        required=required,
        items=resolve_array_items(hint) if _type == "array" else None,
    )