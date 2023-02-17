from fastapi import FastAPI

from src import Container, Agent


# main fastapi app object
app = FastAPI(debug=True, title='Container Agent')


# main (singular) container instance
image_params = {'image_name': 'abc', 'requires': [], 'provides': []}
container = Container(image_params)


@app.get('/', response_model=str)
def get_root():
    return "nothing here"


@app.get('/agents', response_model=list[Agent])
def get_all_containers() -> list[Agent]:
    return container.agents


@app.get('/agents/{agent_id}', response_model=Agent)
def get_agent(agent_id: int) -> Agent | None:
    for agent in container.agents:
        if agent.agent_id == agent_id:
            return agent
    return None


@app.post('/agents', response_model=str)
def post_agent(agent: Agent):
    container.add_agent(agent)


def main():
    container.add_agent(Agent('0', 'type0'))
    container.add_agent(Agent('1', 'type1'))


main()
