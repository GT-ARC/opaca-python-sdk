import os
from typing import Optional, Any
from fastapi import HTTPException


def http_error(code: int, cause: str) -> HTTPException:
    """
    custom http exception like in assessment example solution
    """
    return HTTPException(status_code=code, detail={"cause": cause})
