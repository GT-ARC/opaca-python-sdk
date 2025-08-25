# OPACA API Python Implementation

This module provides an implementation of the OPACA API in Python, using FastAPI to provide the different REST routes.
The 'agents' in this module are not 'real' agents in the sense that they run in their own thread, but just objects that
react to the REST routes.

## Installation

You can install the package by running `pip install opaca` and then `import opaca` into your project files.

## Developing new Agents

Following is a minimal example of how to develop a new agent by using the OPACA Python SDK.

1. Start by creating a new directory for your project and add the following files to it:

    ```
    your_project/
    ├── src/
    │   ├── my_agent.py
    │   └── main.py
    ├── resources/
    │   └── container.json
    ├── Dockerfile
    └── requirements.txt
    ```

2. Then add the following basic contents to these files:

    #### requirements.txt
    
    ```
    opaca
    # Other required packages
    ```
    
    #### Dockerfile
    
    ```
    FROM python:3.12-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . .
    CMD ["python", "main.py"]
    ```
    
    #### resources/container.json
    
    ```
    {
      "imageName": "<your-container-name>"
    }
    ```
    
    #### src/main.py
    
    ```
    from opaca import Container, run
    
    # Create a container based on the container.json file
    container = Container("resources/container.json")
    
    # Initialize the agents. The container must be passed to the agent, to automatically register the agent on the container.
    MyAgent(container=container, agent_id='MyAgent')
    
    # Run the container. This will start a FastAPI server and expose endpoints required for communication within the OPACA framework.
    if __name__ == "__main__":
        run(container)
    ```

3. Finally, define the actual agent class in `src/my_agent.py` by creating a new class inheriting from `opaca.AbstractAgent`. Then add a class method for each action you want to expose and use the `@action` decorator to register it as an OPACA action.

    #### src/my_agent.py

    ```
    from opaca import AbstractAgent, action
    
    class MyAgent(AbstractAgent):
    
        def __init__(self, **kwargs):
            super(MyAgent, self).__init__(**kwargs)
   
        @action
        def add(x: float, y: float) -> float:
            """Returns the sum of numbers x and y."""
            return x + y
    ```

    **Additional Notes**:

   - It is required for all input and output parameters to be annotated with type hints. The type hints are later resolved into JSON schema to be used within HTTP requests.
   - Action methods need to be defined as **non-static**, even if they are not accessing any class attributes or methods. This is to ensure that the method can be pickled and registered as an OPACA action for that agent.
   - You can also use type hints from the `typing` library to define the input and output parameters. This includes types such as `List`, `Dict`, `Tuple`, `Optional`, etc.
   - Agent actions can also be defined `async`.
   - If there are any issues with specific type hints, please open a new [issue in this repository](https://github.com/GT-ARC/opaca-python-sdk/issues), explain what type hint is causing issues, and provide a minimal example. We will try to fix the issue as soon as possible.

## Build and deploy the Agent Container

1. Build your container image from the root directory by using the `Dockerfile` you created: 

    ```
    docker build -t <your-container-name> .
    ```

2. Next, make sure you have a running OPACA Runtime Platform instance. The easiest way to achieve this is by using the published docker image from the [OPACA-Core](https://github.com/gt-arc/opaca-core) repository. (**Note**: Find out your local IP by running `ipconfig` on Windows or `ifconfig` on Linux. `localhost` will not work!)

    ```
    docker container run -d -p 8000:8000 \
   -v /var/run/docker.sock:/var/run/docker.sock \
   -e PUBLIC_URL=http://<YOUR_IP>:8000 \
   -e PLATFORM_ENVIRONMENT=DOCKER ghcr.io/gt-arc/opaca/opaca-platform:main
    ```

3. Finally, you can deploy your container to the running OPACA Platform. For this, you can use the integrated Swagger UI, which will be available at `http://<YOUR_IP>:8000/swagger-ui/index.html` once the OPACA Runtime Platform has been started. Navigate to the `POST /containers` endpoint, click "Try it out", replace the request body with the following content and then click "Execute":
    
    ```
    {
      "image": {
        "imageName": "<your-container-name>"
      }
    }
    ```

    If an uuid is returned, the container has been deployed successfully. You can then test your implemented function by calling the `POST /invoke/{action}` route with your implemented action name and input parameters in the request body.

    An implemented example can be found in [src/sample.py](https://github.com/GT-ARC/opaca-python-sdk/blob/main/src/sample.py).

## Custom Data Types

If your agent is using custom data types as either input or output parameters, you need to register them in the `resources/container.json` file in OpenAPI format. It is recommended to define custom data types with the `BaseModel` class from the [Pydantic](https://pydantic-docs.helpmanual.io/) library.

Here is an example for a custom data type `MyType`:

In your agent class:

```
from pydantic import BaseModel
from typing import List

class MyType(BaseModel):
    var_a: str
    var_b: int = 0
    var_c: List[str] = None
```

In the `resources/container.json` file:

```
{
  "imageName": "<your-container-name>",
  "definitions": {
    "MyType": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "MyType",
      "type": "object",
      "properties": {
        "var_a": {
          "description": "Optional description of var_a.",,
          "type": "string"
        },
        "var_b": {
          "description": "Optional description of var_b.",
          "type": "integer"
        },
        "var_c": {
          "description": "Optional description of var_c.",
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": ["var_a"]
    }
  }
}
```

## Environment Variables

You can pass environment variables to your agent container by declaring them in the `resources/container.json` file and then passing the actual values during the container deployment via the `POST /containers` endpoint.

Here is an example for an environment variable `MY_API_KEY`:

In your `resources/container.json` file:

```
{
  "imageName": "<your-container-name>,
  "parameters": [
    {
        "name": "MY_API_KEY",
        "type": "string",
        "required": true,
        "confidential": true,
        "defaultValue": null
    }
  ]
}
```

During the container deployment, your request body would then look like this:

```
{
  "image": {
    "imageName": "<your-container-name>,
    "parameters": [
      {
        "name": "MY_API_KEY",
        "type": "string",
        "required": true,
        "confidential": true,
        "defaultValue": null
      }
    ]
  },
  "arguments": {
    "MY_API_KEY": "<your-api-key>"
  }
}
```

#### Parameter explanation:

- `name`: The name of the environment variable.
- `type`: The type of the environment variable. Use [JSON schema](https://json-schema.org/understanding-json-schema/reference/type) types.
- `required`: Whether the environment variable is required or not. If `true`, the environment variable must be passed during the container deployment. Otherwise the container deployment will fail.
- `confidential`: If `true`, the value of this environment variable will never be logged or exposed with any OPACA API calls.
- `defaultValue`: The default value of the environment variable. Set to `null` if the parameter is required.

## Additional Information

* All agent classes should extend the `AbstractAgent` class. Make sure to pass a `Container` object to the agent.
* In the agent's constructor `__init__`, you can register actions the agents can perform using the `add_action()` method from the super-class. 
* Alternatively, you can expose actions by using the `@action` decorator on a method.
* Similarly, stream responses can be defined using the `@stream` decorator or the `add_stream()` method in the constructor `__init__`.
* Decorators will use the method name as the action name in PascalCase, the docstring as description, and use type hints to determine the input and output parameter types.
* When registering actions or streams, you can manually specify their name and description by using the `name` and `description` field within the parameter, e.g. `@action(name="MyAction", description="My description")`.
* Methods declared as streams should return some iterator, e.g. by using the `yield` keyword on an iterable.
* Messages from the `/send`  and `/broadcast` routes can be received by overriding the `receive_message()` method.

## Linked Projects

* [OPACA Core](https://github.com/GT-ARC/opaca-core): The OPACA Runtime Platform.
* [OPACA-LLM](https://github.com/GT-ARC/opaca-llm-ui): A complementary LLM integration, autonomously calling agent actions on a connected OPACA Runtime Platform.
