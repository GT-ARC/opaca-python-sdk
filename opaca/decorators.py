import ast
import datetime
import textwrap
import inspect
import re
import logging
import types as base_types
import uuid
from datetime import timedelta
from inspect import iscoroutinefunction

from pydantic import BaseModel
from typing import (Optional, Callable, get_type_hints, Dict,
                    Tuple, Any, Union, get_origin, get_args, TYPE_CHECKING, Iterator, Coroutine)

from .models import StreamDescription, Parameter
from .recurrent_task import RecurrentTask

if TYPE_CHECKING:
    from .abstract_agent import AbstractAgent


log = logging.getLogger(__name__)


def action(
        _func: Optional[Callable] = None,
        *,
        name: str = '',
        description: str = '',
        auth: bool = False
) -> Callable:
    def decorator(func: Callable):
        func._is_action = True
        func._name = name
        func._description = description
        func._auth = auth
        return func

    return decorator(_func) if _func else decorator


def stream(
        *,
        mode: StreamDescription.Mode,
        name: str = '',
        description: str = '',
        auth: bool = False
) -> Callable:
    def decorator(func: Callable):
        func._is_stream = True
        func._mode = mode
        func._name = name
        func._description = description
        func._auth = auth
        return func

    return decorator


def every(
        _func: Callable[[], Coroutine[Any, Any, None]] | None = None,
        *,
        interval: float | datetime.timedelta,
        run_immediately: bool = False,
        task_id: str | None = None,
) -> Callable:
    def decorator(func: Callable):
        func._every_interval = interval
        func._every_run_immediately = run_immediately
        func._every_task_id = task_id
        return func

    return decorator(_func) if _func else decorator


def register_actions(agent: 'AbstractAgent') -> None:
    """
    Auto-register actions marked by decorator.
    """
    for name, func in inspect.getmembers(agent, predicate=inspect.ismethod):
        if not getattr(func, '_is_action', False):
            continue

        params, return_type = parse_params(func)
        action_name = parse_name(func, name)
        description = parse_description(func)

        if getattr(func, '_auth', False):
            check_for_token(action_name, params)

        log.debug(f'REGISTER ACTION: {agent.agent_id} {name} {action_name} {description}, {params}, {return_type}')

        agent.add_action(
            name=action_name,
            description=description,
            parameters=params,
            result=return_type,
            callback=getattr(agent, name),
        )


def register_streams(agent: 'AbstractAgent') -> None:
    """
    Auto-register streams marked by decorator.
    """
    for name, func in inspect.getmembers(agent, predicate=inspect.ismethod):
        if not getattr(func, '_is_stream', False):
            continue

        params, return_type = parse_params(func)
        stream_name = parse_name(func, name)
        description = parse_description(func)

        if getattr(func, '_auth', False):
            check_for_token(stream_name, params)

        mode = getattr(func, '_mode', StreamDescription.Mode.GET)

        log.debug(f'REGISTER STREAM: {agent.agent_id} {name} {stream_name} {mode} {description}, {params}, {return_type}')

        agent.add_stream(
            name=stream_name,
            description=description,
            mode=mode,
            callback=getattr(agent, name),
        )


def register_recurrent(agent: 'AbstractAgent') -> None:
    """
    Auto-register recurrent behaviour marked with @every.
    """
    for name, func in inspect.getmembers(agent, predicate=inspect.ismethod):
        if not hasattr(func, '_every_interval'):
            continue

        if not iscoroutinefunction(func):
            raise ValueError('@every-annotated functions must be async.')

        interval = getattr(func, '_every_interval')
        if isinstance(interval, (float, int)):
            interval = datetime.timedelta(seconds=interval)
        if interval.total_seconds() <= 0:
            raise ValueError('Recurrent task interval must be > 0')

        run_immediately = getattr(func, '_every_run_immediately', False)

        task_id = getattr(func, '_every_task_id', None)
        if task_id is None:
            task_id = f'{agent.agent_id}.{func.__name__}'

        agent.recurrent_tasks[task_id] = RecurrentTask(
            task_id = task_id,
            interval=interval,
            run_immediately=run_immediately,
            callback=func,
        )


def extract_models(hint: Any) -> Iterator[Any]:
    if isinstance(hint, type) and issubclass(hint, BaseModel):
        yield hint
    else:
        for arg in get_args(hint):
            yield from extract_models(arg)


def update_definitions(agent: 'AbstractAgent') -> None:
    """
    Find parameter/result classes that extend Pydantic's BaseModel and auto-generate
    JSON-Schema for those and add it to the definitions section in container.json.
    """
    def make_schema(model_class : type[BaseModel]) -> dict:
        return model_class.model_json_schema()

    base_models = {
        m
        for _, func in inspect.getmembers(agent, predicate=inspect.ismethod)
        if getattr(func, '_is_action', False)
        for v in get_type_hints(func).values()
        for m in extract_models(v)
    }

    definitions = agent.container.image.definitions
    for cls in base_models:
        try:
            if cls.__name__ not in definitions:
                definitions[cls.__name__] = make_schema(cls)
                agent.container.models[cls.__name__] = cls
        except Exception as e:
            log.error(f'Failed to add custom type {cls} to container definitions: {e}')


def check_for_token(name: str, params: Dict[str, Parameter]) -> None:
    if not any(name == "login_token" or getattr(p, "name", None) == "login_token"
               for name, p in list(params.items())):
        raise TypeError(f'The method {name} was declared with "auth" and therefore needs to define '
                        f'the parameter "login_token".')
    if params["login_token"].type != "string":
        raise TypeError(f'The parameter "login_token" in method {name} needs to be defined as a string.')
    params.pop("login_token")


def function_returns_value(func: Callable) -> bool:
    """
    Returns True if the function has any non-None return statements.
    """
    source = inspect.getsource(func)
    source = textwrap.dedent(source)
    tree = ast.parse(source)

    class ReturnVisitor(ast.NodeVisitor):
        def __init__(self):
            self.return_value = False

        def visit_Return(self, node: ast.Return):
            if node.value is not None:
                if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                    self.return_value = True

    visitor = ReturnVisitor()
    visitor.visit(tree)
    return visitor.return_value


def parse_params(func: Callable) -> Tuple[Dict[str, Parameter], Parameter]:
    """
    Parse the decorated function's parameters and return type into proper OPACA model types.
    """
    params = {}
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # Transform parameter type hints
    for p_name, p_val in sig.parameters.items():
        if p_name == 'self':
            continue
        if p_val.annotation is inspect.Parameter.empty:
            raise TypeError(f'Parameter "{p_name}" in function "{func.__name__}" is missing a type annotation, '
                            f'which is required for the decorator to work')
        hint = type_hints.get(p_name, None)
        params[p_name] = python_type_to_parameter(hint, p_val.default)

    # Check return type
    if sig.return_annotation is not inspect.Parameter.empty:
        return_type = type_hints.get('return', None)
        return_type = python_type_to_parameter(return_type)
    elif function_returns_value(func):
        # Raise error if function returns anything but no return type is provided
        raise TypeError(f'Function "{func.__name__}" has non-None return statements but missing a return type annotation')
    else:
        return_type = python_type_to_parameter(None)

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
    description: str = getattr(func, '_description', '')
    docstring: str = inspect.getdoc(func) or ''
    return description or docstring


type_mapping: dict[type, str] = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


type_priority: dict[str, int] = {
    "null": 0,
    "boolean": 1,
    "integer": 2,
    "number": 3,
    "string": 4,
    "array": 5,
    "object": 6,
}


def merge_json_types(types: list[str]) -> str:
    """
    If more than one parameter type was given for a single parameter (e.g. with Union),
    decide which single parameter type would fit best, based on the type priority above.
    """
    if len(types) == 1:
        return types[0]

    # Handle int + float = number
    if "integer" in types and "number" in types:
        types = [t for t in types if t != "integer"]

    # Choose the highest precedence type
    best_type = max(types, key=lambda t: type_priority.get(t, -1))

    # If any types are incompatible, raise error
    if len(types) > 1 and best_type not in {"number", "array", "object"}:
        raise TypeError(f'Cannot merge types {types} into one JSON schema type')

    return best_type


def resolve_array_items(hint: Any) -> Parameter.ArrayItems:
    """
    Recursive function to resolve array items.
    """
    origin = get_origin(hint) or hint
    args = get_args(hint)

    if origin in {list, tuple} and args:
        inner = args[0]
        if _type := next((arg.__name__ for arg in args if issubclass(arg, BaseModel)), None):
            return Parameter.ArrayItems(type=_type)
        elif (get_origin(inner) or inner) in {list, tuple}:
            return Parameter.ArrayItems(
                type="array",
                items=resolve_array_items(inner),
            )
        return Parameter.ArrayItems(type=type_mapping.get(get_origin(inner) or inner, inner.__name__))
    else:
        return Parameter.ArrayItems(type=type_mapping.get(origin, hint.__name__))


def python_type_to_parameter(hint: Any, default: Any = inspect.Parameter.empty) -> Any:
    """
    This method takes in parameter information and transforms it into a Parameter instance.
    Supports nested parameter types and custom objects.
    """
    origin = get_origin(hint) or hint
    args = get_args(hint)

    required = default is inspect.Parameter.empty
    default_value = None if (default is inspect.Parameter.empty) else default

    # Handle NoneType
    if hint is None:
        _type = "null"
    # Handle Union types with None or Optionals (Optional[str] == Union[str, None])
    elif origin in (Union, base_types.UnionType):
        types = []

        # Set required to False if any "None" type is found
        if any(arg is type(None) for arg in args):
            required = False

        # Check for custom types in the Union. Use the first one that has been found. Disregard the rest.
        # Union[CustomType, None] --> will work ; Union[CustomType, str] --> will disregard "str"
        if not (_type := next((arg.__name__ for arg in args if issubclass(arg, BaseModel)), None)):
            for arg in args:
                # Skip None types to avoid defaulting to "object"
                if arg is type(None): continue
                t = type_mapping.get(get_origin(arg), "object")
                types.append(t)

                # If Union includes an array for further deserialization,
                # overwrite the current "Union" hint with the list/tuple hint
                # This has probably some weird side effects for nested Unions/Optionals
                if get_origin(arg) in {list, tuple}:
                   hint = arg
            try:
                _type = merge_json_types(types)
            except TypeError as e:
                raise ValueError(f'Unsupported Union types {args}: {e}')
    else:
        # Use the custom object name if the hint is a class, otherwise use standard type names
        _type = type_mapping.get(origin, hint.__name__)

    return Parameter(
        type=_type,
        required=required,
        defaultValue=default_value,
        items=resolve_array_items(hint) if _type == "array" else None,
    )

