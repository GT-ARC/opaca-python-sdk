import os
from fastapi import HTTPException


def http_error(code: int, cause: str) -> HTTPException:
    """
    custom http exception like in assessment example solution
    """
    return HTTPException(status_code=code, detail={"cause": cause})


def get_environment_variable(name: str):
    if name in os.environ:
        return os.environ.get(name)
    return ''
