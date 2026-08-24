from pathlib import Path
import mimetypes as mime
from fastapi import HTTPException
from starlette.responses import FileResponse


def http_error(code: int, cause: str) -> HTTPException:
    """Shorthand for HTTPException"""
    return HTTPException(status_code=code, detail={"cause": cause})


def make_file_response(path: str | Path) -> FileResponse:
    mime_type = mime.guess_type(path)[0]
    return FileResponse(path, media_type=mime_type, status_code=200)