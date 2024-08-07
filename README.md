# OPACA API Python Implementation

This module provides an implementation of the OPACA API in Python, using FastAPI to provide the different REST routes.
The 'agents' in this module are not 'real' agents in the sense that they run in their own thread, but just objects that
react to the REST routes.

## Developing new Agents

An example for how to develop new agents using this module can be found in `sample.py`.
The most important take-aways are:
* All agent classes should extend the `AbstractAgent` class.
* In the constructor `__init__`, you can register actions the agents can perform using the `add_action()` method from the super-class. 
* Similarly, stream responses can be defined using the `add_stream()` method.
* When registering actions, the `callback` parameter expects a method or function that the defined `parameters` can be exactly applied to.
* The `callback` for stream responses should return some iterator using the `yield` keyword.
* Messages from the `/send`  and `/broadcast` routes can be received by overriding the `receive_message()` method.


## Building the Image and running the Container

* `$ docker build -t sample-container-python .`
* `$ docker run -p 8082:8082 sample-container-python`
* Open http://localhost:8082/docs#/

Or deploy the container to a running OPACA Runtime Platform and call it via the Platform's API.
