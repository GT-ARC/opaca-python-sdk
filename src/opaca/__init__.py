from fastapi import FastAPI as _FastAPI

from .decorators import action, stream
from .routes import create_routes
from .container import Container
from .abstract_agent import AbstractAgent
from .models import (Parameter,
                     ActionDescription,
                     AgentDescription,
                     StreamDescription,
                     Message)


def run(title: str,
        container: Container,
        host: str | None = None,
        port: int | None = None,
        app: _FastAPI | None = None,
    ) -> None:
    """
    Run the container with uvicorn.

    :param title: The title of the application.
    :param container: The agent container to run the application with.
    :param host: The hostname to run the application on. Defaults to '0.0.0.0'.
    :param port: The port to run the application on. Defaults to the apiPort specified in the container image.
    :param app: The FastAPI object with the routes. If this is provided,
    the title argument becomes irrelevant. Defaults to the standard OPACA routes.
    """
    if host is None:
        host = '0.0.0.0'

    if port is None:
        port = container.image.apiPort

    if app is None:
        app = create_routes(title, container)

    import uvicorn
    uvicorn.run(app, host=host, port=port)
