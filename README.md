**Developing new Agents**

An example for how to develop new agents using this module can be found in `src/SampleAgent.py`.
The most important take-aways are:
* All agent classes should extend the `AbstractAgent` class.
* In the constructor `__init__`, you can register actions the agents can perform using the `add_action()` function from the super-class. 
* Similarly, stream responses can be defined using the `add_stream()` function.
* When registering actions, the `callback` parameter expects a function that the defined `parameters` can be exactly applied to.
* The `callback` for stream responses should return some iterator using the `yield` keyword.
* Messages from the `/send`  and `/broadcast` routes can be received by overriding the `receive_message()` function.

**Building the Image and running the Container**

* `$ docker build -t sample-container-python .`
* `$ docker run -p 8082:8082 sample-container-python`
* Open http://localhost:8082/docs#/
