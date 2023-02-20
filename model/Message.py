from pydantic import BaseModel


class Message(BaseModel):

    payload: dict
    replyTo: str
