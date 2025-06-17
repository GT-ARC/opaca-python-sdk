# OPACA API Python Implementation

This module provides an implementation of the OPACA API in Python, using FastAPI to provide the different REST routes.
The 'agents' in this module are not 'real' agents in the sense that they run in their own thread, but just objects that
react to the REST routes.

## Installation

This module has been deployed to PyPI (see https://pypi.org/project/opaca/), so in order to use it, you can just
`pip install opaca` and then `import opaca` into your project.

## Developing new Agents

An example for how to develop new agents using this module can be found in `sample.py`.
The most important take-aways are:
* All agent classes should extend the `AbstractAgent` class.
* In the constructor `__init__`, you can register actions the agents can perform using the `add_action()` method from the super-class. 
* Alternatively, you can expose actions by using the `@action` decorator on a method.
* Similarly, stream responses can be defined using the `@stream` decorator or the `add_stream()` method in the constructor `__init__`.
* Decorators will use the method name as the action name in PascalCase, the docstring as description, and use type hints to determine the input and output parameter types.
* When registering actions or streams, you can manually specify their name and description by using the `name` and `description` field within the parameter, e.g. `@action(name="MyAction", description="My description")`.
* Methods declared as streams should return some iterator using the `yield` keyword.
* Messages from the `/send`  and `/broadcast` routes can be received by overriding the `receive_message()` method.


## Building the Image and running the Container

* `$ docker build -t sample-container-python .`
* `$ docker run -p 8082:8082 sample-container-python`
* Open http://localhost:8082/docs#/

Or deploy the container to a running OPACA Runtime Platform and call it via the Platform's API.
