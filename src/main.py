import json

from opaca_py.container import Container
from opaca_py.routes import create_routes
from opaca_py.models import ImageDescription
from opaca_py.utils import http_error, get_env_var

from sample import SampleAgent


def load_image(json_file: str) -> ImageDescription:
    try:
        with open(json_file, encoding='utf-8') as f:
            return ImageDescription(**json.load(f))
    except TypeError:
        return http_error(500, 'Failed to load image description.')


def main():
    import uvicorn

    # assemble Agent Container
    image = load_image("resources/container.json")
    container = Container(image)
    agent1 = SampleAgent(agent_id='sampleAgent1', agent_type='type1')
    container.add_agent(agent1)
    agent1.subscribe_channel('test_channel')

    print(image)
    print(container.get_description())

    # Start App
    app = create_routes("sample-container", container)
    uvicorn.run(app, host="0.0.0.0", port=container.image.apiPort)


main()
