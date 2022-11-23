from importlib.resources import files
from pathlib import Path
from shutil import copyfile

from comoda import a_logger
from comoda.yaml import load

from omnia import __appname__, config_dir, log_file


class ConfigurationManager:
    def __init__(self, args=None, config_filename="config.yaml"):
        def copy_config_file_from_package(dst):
            _from_package = files("config").joinpath("config.yaml")
            copyfile(_from_package, dst)

        loglevel = "INFO" if args is None else args.loglevel
        logfile = log_file if args is None else args.logfile
        logger = a_logger(
            self.__class__.__name__, level=loglevel, filename=logfile
        )

        if args and args.configuration_file:
            configuration_file = Path(args.configuration_file)
            if not configuration_file.exists():
                msg = "{} file not found. Please check the path".format(
                    configuration_file
                )
                logger.error(msg)
                exit(msg)
        else:
            # Create configuration file from default if needed
            configuration_file = Path(config_dir, config_filename)
            if not configuration_file.exists():
                configuration_file.parent.mkdir(parents=True, exist_ok=True)
                logger.warning(
                    "Copying default config file from {} package "
                    "resource to {}".format(__appname__, configuration_file)
                )
                copy_config_file_from_package(configuration_file)
                logger.warning(
                    "Updates default path settings in the config file at {}".format(
                        configuration_file
                    )
                )

        logger.debug("Reading configuration from {}".format(configuration_file))
        c = load(configuration_file)

        mdb_connection = c["mdbc"]
        self.mdbc_alias = mdb_connection["alias_label"]
        self.mdbc_username = mdb_connection["username"]
        self.mdbc_password = mdb_connection["password"]
        self.mdbc_hostname = mdb_connection["hostname"]
        self.mdbc_port = mdb_connection["port"]
        self.mdbc_db = mdb_connection["db"]
        self.mdbc_auth_mech = mdb_connection["auth_mech"]
        self.mdbc_auth_source = mdb_connection["auth_source"]

        self.loglevel = c["loglevel"]
        self.logformat = c["logformat"]

    @property
    def get_mdbc_alias(self):
        return self.mdbc_alias

    @property
    def get_mdbc_username(self):
        return self.mdbc_username

    @property
    def get_mdbc_password(self):
        return self.mdbc_password

    @property
    def get_mdbc_port(self):
        return self.mdbc_port

    @property
    def get_mdbc_db(self):
        return self.mdbc_db

    @property
    def get_mdbc_auth_mech(self):
        return self.mdbc_auth_mech

    @property
    def get_mdbc_auth_source(self):
        return self.mdbc_auth_source

    @property
    def get_mdbc_hostname(self):
        return self.mdbc_hostname

    @property
    def get_loglevel(self):
        return self.loglevel

    @property
    def get_logformat(self):
        return self.logformat
