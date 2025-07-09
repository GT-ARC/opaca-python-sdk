from fastapi import FastAPI

from .decorators import action, stream
from .routes import create_routes
from .container import Container
from .abstract_agent import AbstractAgent
from .models import (Parameter,
                     ActionDescription,
                     AgentDescription,
                     StreamDescription,
                     Message)


def run(title: str, container: Container, app: FastAPI | None = None) -> None:
    """
    Run the container with uvicorn.
    """
    if app is None:
        app = create_routes(title, container)

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)
