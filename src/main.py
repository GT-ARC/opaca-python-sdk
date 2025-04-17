from opaca_py.container import Container
from opaca_py.routes import create_routes

from sample import SampleAgent


# assemble Agent Container
container = Container("resources/container.json")
agent1 = SampleAgent(agent_id='sampleAgent1', agent_type='type1')
container.add_agent(agent1)
agent1.subscribe_channel('test_channel')

# Create App
app = create_routes("sample-container", container)


if __name__ == "__main__":
    # start app (alternatively, start with `uvicorn` from command line)
    import time
    import uvicorn
    time.sleep(15)

    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)
