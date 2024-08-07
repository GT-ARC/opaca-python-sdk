import json
import os
from typing import Optional, Any

from .models import ImageDescription

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


def load_image(json_file: str) -> ImageDescription:
    try:
        with open(json_file, encoding='utf-8') as f:
            return ImageDescription(**json.load(f))
    except TypeError:
        return http_error(500, 'Failed to load image description.')

