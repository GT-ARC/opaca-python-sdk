from pydantic import BaseModel


class ImageDescription(BaseModel):

    imageName: str
    requires: list[str]
    provides: list[str]
    name: str = ''
    description: str = ''
    provider: str = ''
