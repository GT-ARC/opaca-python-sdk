# CHANGELOG

All changes to the opaca package will be documented in this file.

## [0.0.4] - not released yet

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