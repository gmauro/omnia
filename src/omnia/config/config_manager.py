from importlib.resources import files
from pathlib import Path
from shutil import copyfile

from pydantic import ValidationError
from ruamel.yaml import YAML

from .. import __appname__, config_dir, config_filename, logger
from .config_models import Configuration


class SingletonConfigurationManager(type):
    """Metaclass."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigurationManager(metaclass=SingletonConfigurationManager):
    def __init__(self, **kwargs):
        def copy_config_file_from_package(dst):
            package_name = ".".join([__appname__, "config"])
            _from_package = files(package_name).joinpath(config_filename)
            copyfile(_from_package, dst)

        # Check if a custom config file is provided
        custom_config_file = kwargs.get("cf")
        if custom_config_file:
            configuration_file = Path(custom_config_file)
            if not configuration_file.exists():
                msg = f"{configuration_file} file not found. Please check the path"
                logger.error(msg)
                exit(msg)
        # If no custom config is provided, use the default one
        else:
            # Create configuration file from default if needed
            configuration_file = Path(config_dir, config_filename)
            if not configuration_file.exists():
                configuration_file.parent.mkdir(parents=True, exist_ok=True)
                logger.warning(
                    f"Copying default config file from {__appname__} package resource to {configuration_file}"
                )
                copy_config_file_from_package(configuration_file)
                logger.warning(f"Configuration file has default values! Update them in {configuration_file}")

        logger.debug(f"Reading configuration from {configuration_file}")
        yaml = YAML(typ="safe")
        with open(configuration_file) as file:
            c = yaml.load(file)

        try:
            config = Configuration(**c)
        except (ValidationError, TypeError) as e:
            logger.error(f"Configuration validation error: {e}")
            exit(f"Configuration validation error: {e}")

        default_profile_name = config.default_profile
        profile_name_from_cli = kwargs.get("profile")

        if profile_name_from_cli:
            if profile_name_from_cli not in config.profiles:
                exit(f"The {profile_name_from_cli} profile name is invalid. Check it")
            self.profile = config.profiles[profile_name_from_cli]
        else:
            self.profile = config.profiles[default_profile_name]

        self.uri_from_cli = kwargs.get("uri")

    @property
    def mongodb_uri(self) -> str:
        """Get the database connection settings from the kwargs. If they are not present, use the config."""

        def _construct_mongodb_uri(prefix, profile):
            auth_part = (
                f"{profile.username}:{profile.password}@"
                if (hasattr(profile, "username") and profile.username)
                and (hasattr(profile, "password") and profile.password)
                else ""
            )
            port_part = f":{profile.port}" if prefix != "mongodb+srv" else ""
            uri = f"{prefix}://{auth_part}{profile.host}{port_part}/{profile.database}"

            # Add options to the URI
            if hasattr(profile, "options") and profile.options:
                options_str = "&".join(f"{key}={value}" for key, value in vars(profile.options).items() if value)
                uri += f"?{options_str}"

            return uri

        if self.uri_from_cli:
            return self.uri_from_cli

        profile = self.profile

        if hasattr(profile, "prefix"):
            prefix = profile.prefix
        else:
            prefix = "mongodb"

        # Construct the MongoDB URI
        uri = _construct_mongodb_uri(prefix, profile)

        return uri
