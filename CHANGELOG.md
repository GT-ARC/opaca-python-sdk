# CHANGELOG

All changes to the opaca package will be documented in this file.

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