from typing import List, Dict, Any, Annotated, AsyncIterator
from fastapi import FastAPI, APIRouter
from fastapi.params import Header, Depends
from starlette.responses import StreamingResponse, FileResponse
from contextlib import asynccontextmanager

from .container import Container
from .keycloak_utils import create_token_dependency
from .models import Message, AgentDescription, ContainerDescription, StreamDescription, Login


def create_routes(title: str, container: Container) -> FastAPI:
    """
    Create FastAPI instance providing the different REST routes for the OPACA API and
    calling the respective methods of the given container instance. The application
    still has to be run with `uvicorn.run(app, ...)`.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        container.start_recurrent_tasks()
        yield
        container.cancel_recurrent_tasks()

    app = FastAPI(
        debug=True,
        title=title,
        lifespan=lifespan,
    )

    app.include_router(_create_protected_routes(container))
    app.include_router(_create_public_routes(container))

    return app


def _create_public_routes(container: Container) -> APIRouter:
    """
    These routes are always publicly available and never require an access token.
    """
    router = APIRouter()

    @router.get('/files/{file_id}', response_class=FileResponse)
    async def get_file(file_id: str) -> FileResponse:
        """
        GET a file exposed via the expose_file() function.
        """
        return container.serve_exposed_file(file_id)

    return router


def _create_protected_routes(container: Container) -> APIRouter:
    """
    If auth is enabled, these routes require a valid Bearer token.
    """
    check_token = create_token_dependency(container)
    router = APIRouter(dependencies=[Depends(check_token)])

    @router.get('/info', response_model=ContainerDescription)
    async def get_container_info() -> ContainerDescription:
        """
        Get a description of the container.
        """
        return container.make_model()

    @router.get('/agents', response_model=List[AgentDescription])
    async def get_all_agents() -> List[AgentDescription]:
        """
        Get a list of all agents and their corresponding actions.
        """
        return container.make_agent_models()

    @router.get('/agents/{agentId}', response_model=AgentDescription)
    async def get_agent(agentId: str) -> AgentDescription:
        """
        Returns the agent with the passed agentId.
        """
        return container.get_agent(agentId).make_model()

    @router.post('/send/{agentId}')
    async def send_message(agentId: str, message: Message) -> None:
        """
        Send a message to the specified agent.
        """
        container.send_message(agentId, message)

    @router.post('/broadcast/{channel}')
    async def broadcast(channel: str, message: Message) -> None:
        """
        Broadcast a message to all agents that listen on the channel.
        """
        container.broadcast(channel, message)

    @router.post('/invoke/{action}', response_model=Any)
    async def invoke_action(action: str, parameters: Dict[str, Any],
                            ContainerLoginToken: Annotated[str | None, Header()] = None) -> Any:
        """
        Invoke the specified action on any agent that knows the action.
        """
        return await container.invoke_action(action, parameters,
                                             ContainerLoginToken.strip('"') if ContainerLoginToken else None)

    @router.post('/invoke/{action}/{agentId}', response_model=Any)
    async def invoke_agent_action(action: str, agentId: str, parameters: Dict[str, Any],
                                  ContainerLoginToken: Annotated[str | None, Header()] = None) -> Any:
        """
        Invoke an action on a specific agent.
        """
        return await container.invoke_agent_action(action, agentId, parameters,
                                                   ContainerLoginToken.strip('"') if ContainerLoginToken else None)

    @router.get('/stream/{stream}', response_class=StreamingResponse)
    async def get_stream(stream: str, ContainerLoginToken: Annotated[str | None, Header()] = None) -> StreamingResponse:
        """
        GET a stream from any agent.
        """
        token = ContainerLoginToken.strip('"') if ContainerLoginToken else None
        return _make_stream_response(container, stream, StreamDescription.Mode.GET, login_token=token)

    @router.get('/stream/{stream}/{agentId}', response_class=StreamingResponse)
    async def get_agent_stream(stream: str, agent_id: str,
                               ContainerLoginToken: Annotated[str | None, Header()] = None) -> StreamingResponse:
        """
        GET a stream from the specified agent.
        """
        token = ContainerLoginToken.strip('"') if ContainerLoginToken else None
        return _make_stream_response(container, stream, StreamDescription.Mode.GET, agent_id, token)

    @router.post('/login')
    async def handle_login(login: Login) -> str:
        """
        Provide login credentials required for actions requiring authentication.
        """
        return await container.handle_login(login)

    @router.post('/logout')
    async def handle_logout(ContainerLoginToken: Annotated[str | None, Header()] = None) -> bool:
        """
        Performs a logout operation.
        """
        token = ContainerLoginToken.strip('"') if ContainerLoginToken else None
        return await container.handle_logout(token)

    return router


def _make_stream_response(
        container: Container,
        name: str,
        mode: StreamDescription.Mode,
        agent_id: str | None = None,
        login_token: str | None = None
) -> StreamingResponse:
    """
    Converts the byte stream from the stream invocation into the correct response format.
    """
    result = container.invoke_stream(name, mode, login_token) if agent_id is None \
        else container.invoke_agent_stream(name, mode, agent_id, login_token)

    # workaround for empty response, e.g. from POST streams
    if not result: result = iter([])

    return StreamingResponse(result, media_type='application/octet-stream')
