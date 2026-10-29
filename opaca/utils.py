from pathlib import Path
import mimetypes as mime
from typing import Any

from fastapi import HTTPException
from starlette.responses import FileResponse


def http_error(code: int, cause: str, headers: Any | None = None) -> HTTPException:
    """Shorthand for HTTPException"""
    return HTTPException(status_code=code, detail={"cause": cause}, headers=headers)


def make_file_response(path: str | Path) -> FileResponse:
    mime_type = mime.guess_type(path)[0]
    return FileResponse(path, media_type=mime_type, status_code=200)