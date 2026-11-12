# CHANGELOG

All changes to the opaca package will be documented in this file.

## [0.0.10] - 2026-11-12

### Added

- New `@every` decorator for recurrent agent behaviour that is executed on a fixed interval.
- Agents can contact their parent platform via the built-in `self.platform_client`.
- Custom `BaseModel` types in `Optional` action parameters are now also parsed automatically.
- Keycloak authentication: if `KEYCLOAK_URL` is set, all container routes (except `GET /files/{file_id}`) require a valid access token issued to the container's parent platform.
- The `platform_client` authenticates against the parent platform with its own Keycloak client token, which is renewed automatically.
- `AsyncOpacaClient` now renews its access token automatically after `platform_login()`, using the refresh token: before a request if the token is about to expire, and on a `401`. Without a login, requests are sent without a token, so platforms without auth work as before.
- Tokens are now stored together with their expiry time (`access_token.expires_at`).
- New sample action `broadcast_message` in the example, to test the platform client and token handling.

### Changed

- **Breaking:** `AsyncOpacaClient.token` was replaced by `access_token` and `refresh_token` (`KeycloakToken` objects; the raw token is in `.token`).
- **Breaking:** `AsyncOpacaClient.renew_token()` was renamed to `platform_login_renew()`. It now uses the refresh token from `platform_login()`.
- **Breaking:** `platform_login()` and `platform_login_renew()` now expect the platform's `/login` and `/login/renew` routes to return an access and refresh token pair, so they need a platform version that does.
- **Breaking:** `get_file_url()` and `find_own_url()` are now `async`, so actions using them have to be `async` too.
- **Breaking:** The `opaca.client` module was moved to `opaca.clients`. `from opaca import AsyncOpacaClient` still works.
- **Breaking:** Python 3.12 or newer is now required.
- **Breaking:** `AbstractAgent.make_description()` and `Container.get_description()` were renamed to `make_model()`. Several internal helpers were made private.
- The `TOKEN` environment variable and `Container.token` were removed.

### Fixed

- Fixed `GET /stream/{stream}/{agentId}` not resolving the `agentId` path parameter.

## [0.0.9] - 2026-09-07

### Added

- `BaseModel` classes that are used as the types of action parameters or return values now have their schemas auto-registered into the container's `definitions`. This also applies when they are nested in list types.
- New sample action and `BaseModel` type to showcase the auto-registering in the example.
- New `Connectivity` model class that was previously missing.

### Fixed

- Fixed error handling when invoking actions so that unrelated internal `TypeErrors` are no longer hidden behind an "invalid action parameters" message.
- Added many missing type hints.

## [0.0.8] - 2026-07-15

### Added

- Action parameters can now declare default values. Any omitted parameters are automatically filled in before invoking the action.
- New `expose_file(path)` method on `AbstractAgent` (and `Container`) to make a file publicly available via the built-in `GET /files/{file_id}` route. Also added a `get_file_url(file_id)` helper to retrieve the full URL of an exposed file.
- `AsyncOpacaClient` now accepts a `timeout` parameter at construction time as the default for all requests. You can also override this with an individual timeout per request.
- `get_agents()` and `get_containers()` on `AsyncOpacaClient` now accept an `include_connected` parameter to include agents/containers from connected platforms.

### Changed

- `AsyncOpacaClient` default timeout changed from a hardcoded `10s` to `None` (no timeout).



## [0.0.7] - 2026-04-08

### Added

- New `AsyncOpacaClient` that can be used easily and asynchronously interact with a running OPACA Runtime Platform via its API.
- `handle_login` and `handle_logout` methods can now be declared either  async or non-async.

### Changed

- Switched build system from `pip`/`requirements.txt` to `uv` for faster and more reliable dependency management.
- Reorganized project structure: package source files moved to `opaca/` directory; example files moved to `example/` with their own minimal requirements.
- Improved type hint coverage and general code readability across core modules.

## [0.0.6] - 2025-10-16

### Added

- Added "Container Login":
  - Containers can now handle user credentials for authentication.
  - Agents can define a `handle_login` and `handle_logout` method.
  - The action decorator now accepts an `auth` parameter. If set to `True`, the action will need to define `login_token: str` as a parameter, which will provide the current login_token of the request user, after successful authentication.
  - During `handle_login`, a username, password, and a UUID are provided. You can then use these information to authenticate to an external service and manage credentials within your custom container.
  - An example implementation can be found in the [sample agent](src/sample.py).
- Added an example in [README.md](README.md#custom-routes) implementing custom endpoints to your container.

### Changed

- Improved the underlying action- and stream descriptions during registering.

### Fixed

- Fixed an issue for dependency resolution for third party packages when installing `opaca`.
- Fixed an incorrect container image path in [main.py](src/main.py).


## [0.0.5] - 2025-08-27

### Added

- Agent actions and streams with the `@action`/`@stream` decorators can now be declared `async`.
- Added a simplified startup guide to the [README](README.md).

### Changed

### Fixed

- List type hints in `Optional` or `Union` are now correctly resolved.
- Fixed the sample agent files to follow the simplified startup process.

## [0.0.4] - 2025-07-23

### Added

- Raise an error when a decorated function with parameters has no type hints
- Raise an error for missing return type annotations when function returns non-None type
- New `opaca.run(container)` method to quickly and easily start the container without hassle.

### Changed

- Each `AbstractAgent` now needs to be passed a `Container` on creation that it is immediately added to.

### Fixed

- Fixed a bug for type hints in decorators for nested types in List
- Fixed a bug for NoneType mapping to type "null"

## [0.0.3] - 2025-06-25
 
### Added

- OPACA agents can now include a description
- Added the project repository link to the project metadata
   
### Changed
 
### Fixed

## [0.0.2] - 2025-06-10
 
### Added
   
### Changed
 
### Fixed

- Fixed an issue with incorrect parameter type mapping for native python types.

## [0.0.1] - 2025-06-05
 
### Added

- Initial push of the opaca package providing helpful functions to create agent containers suitable to be used within the OPACA framework.
   
### Changed
 
### Fixed