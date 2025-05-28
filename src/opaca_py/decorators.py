import inspect
import re
from typing import Optional, Callable, get_type_hints, Dict, Tuple, Any, Union, get_origin, get_args

from .models import StreamDescription, Parameter


def action(_func: Optional[Callable] = None, *, name: str = '', description: str = ''):
    def decorator(func: Callable):
        func._is_action = True
        func._name = name
        func._description = description
        return func

    return decorator(_func) if _func else decorator


def stream(*, mode: StreamDescription.Mode, name: str = '', description: str = ''):
    def decorator(func: Callable):
        func._is_stream = True
        func._mode = mode
        func._name = name
        func._description = description
        return func

    return decorator


def register_actions(agent):
    """
    Auto-register actions marked by decorator.
    """
    for name, func in inspect.getmembers(agent, predicate=inspect.ismethod):
        if not getattr(func, '_is_action', False):
            continue

        params, return_type = parse_params(func)
        action_name = parse_name(func, name)
        description = parse_description(func)

        agent.add_action(
            name=action_name,
            description=description,
            parameters=params,
            result=return_type,
            callback=getattr(agent, name),
        )


def register_streams(agent):
    """
    Auto-register streams marked by decorator.
    """
    for name, func in inspect.getmembers(agent, predicate=inspect.ismethod):
        if not getattr(func, '_is_stream', False):
            continue

        stream_name = parse_name(func, name)
        description = parse_description(func)
        mode = getattr(func, '_mode', '')

        agent.add_stream(
            name=stream_name,
            description=description,
            mode=mode,
            callback=getattr(agent, name),
        )


def parse_params(func: Callable) -> Tuple[Dict[str, Parameter], Parameter]:
    """
    Parse the decorated function's parameters and return type into proper OPACA model types.
    """
    params = {}
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    for p_name, p_val in sig.parameters.items():
        if p_name == 'self':
            continue
        hint = type_hints.get(p_name, None)
        params[p_name] = python_type_to_parameter(hint, p_val.default)
    return_type = type_hints.get('return', None)
    return_type = python_type_to_parameter(return_type)
    return params, return_type


def parse_name(func: Callable, func_name: str) -> str:
    """
    Parse the name of the decorated function into a proper action/stream name.
    """
    action_name = getattr(func, '_name', '')
    if not action_name:
        action_name = ''.join(word.capitalize() for word in re.split(r'[_\-]', func_name))
    return action_name


def parse_description(func: Callable) -> str:
    """
    Parse the description of the decorated function into a proper action/stream description.
    """
    description = getattr(func, '_description', '')
    if not description and func.__doc__:
        description = func.__doc__.strip()
    return description


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
