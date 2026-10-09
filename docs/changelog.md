# Changelog

All notable changes to this project will be documented in this file.

[Git history](https://github.com/ht-diva/gwasstudio/commits/main/)
## [0.6.2] - 2026-10-09

### 🐛 Bug Fixes

- Update the Dockerfile to fix the image build and add a dedicated user

## [0.6.1] - 2026-10-08

### 💼 Other

- Bump version

### ⚙️ Miscellaneous Tasks

- Update docker build environment

## [0.6.0] - 2026-10-08

### 🚀 Features

- Add versioned trees, curated views, and scientist-friendly data access

## [0.5.0] - 2025-09-26

### 🚀 Features

- Switch models to Datacatalog and Dataset
- Add dataset registration and retrieval commands
- Remove connection manager context from cli commands
- Implement the deletion of the collection and deregistration of its contents

### 🐛 Bug Fixes

- Fix how edit_collection manage None value
- Use glob to recursively find all files matching the pattern for file registration.
- Update test action
- Start the embedded mongodb when needed

### 🚜 Refactor

- Establish common functions for the cli
- Cli, config_manager, profiles for the connections, new config file format
- Split dataset retrieval and registration in different modules
- Implement the MongoWrapperMixin class

## [0.4.0] - 2025-08-29

### 🚀 Features

- Move forward to poetry v2
- Major refactoring, implement collections handling and dataobjects addition.
- Add support for the list of metadata for data objects and collections
- Update the models to better handle the unique_key and the context manager; reformat the cli for listings
- Add basic fast_api app
- Add notes option to Dataset model

### 🐛 Bug Fixes

- Move context manager out from models
- File registration minor

### 💼 Other

- Bump version

### 🚜 Refactor

- Organize commands by sections

## [0.3.2] - 2023-06-27

### 💼 Other

- Add references and show dataidentifier
- Move cli commands into their folder
- Start to refactored the Command Line Interface to use Click + Cloup instead of argparse
- Remove epilog
- Cleanup after some time
- Set up github action for testing
- Install poetry
- Use py 3.11
- Add dev dependencies
- Use py 3.10
- Use python3
- Change github action for testing
- Simplify log handling
- Add github action to build the docker image from the main branch
- Add Dockerfile
- Reformat did model and use a mixin class; add tests
- Update some cli commands
- Improve show command to handle both object types
- Set the order
- Generalize the code to properly handle different categories of data

## [0.3.1] - 2023-04-27

### 💼 Other

- Starts using Poetry
- Remove cache files
- Bump version

### 🚜 Refactor

- Refactoring get_mec and info variables

## [0.3.0] - 2023-04-22

### 💼 Other

- Add delete command
- Add collections and tags fields to the model
- Add a better description
- Update view action
- Add view cli
- Add collection object
- Add config path
- Improve collections and dates in models
- Improve db connection arguments handling
-  bump mongoengine version, add mongomock
- Start to test models
- Update PosixDataObject, add more tests
- Improve cli description
- Bump mongoengine version
- Specify the mongo_client_class
- Remove alias from connection
- Add data identifier module
- Bump version

## [0.2.0] - 2022-11-20

### 🐛 Bug Fixes

- Fix the deletion of the object

### 💼 Other

- First import
- Add gitignore
- Add info cli
- Update gitignore
- Bump comoda version
- Change the label of the attribute from zone to host
- Add reg command
- Read configuration from file
- Bump version

### 🚜 Refactor

- Refactor command-line interface
- Refactoring
