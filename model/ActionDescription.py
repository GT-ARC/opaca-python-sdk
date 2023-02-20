from pydantic import BaseModel


class ActionDescription(BaseModel):

    name: str
    parameters: dict[str, str]
    result: str
