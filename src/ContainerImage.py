from typing import Optional
from pydantic import BaseModel


class ContainerImage(BaseModel):

    image_name: str
    requires: list
    provides: list

    name: Optional[str]
    description: Optional[str]
    provider: Optional[str]

    def __init__(self, **kwargs):
        super(ContainerImage, self).__init__(**kwargs)
