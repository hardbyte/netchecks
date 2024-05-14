import json
import os
from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, BaseSettings
from structlog import get_logger

logger = get_logger()


def json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a JSON file
    pointed at by an environment variable.

    The environment variable name is loaded from the default config.
    """
    settings_environment_variable_name = settings.__config__.settings_environment_variable_name

    if settings_environment_variable_name in os.environ:
        config_file_path = Path(os.environ.get("JSON_CONFIG"))
        logger.debug("Setting config from file", config_file_path=config_file_path)
        return json.loads(config_file_path.read_text())
    else:
        logger.debug("Not loading config from file")
        return {}


class MetricsConfig(BaseModel):
    port: int = 9090
    enabled: bool = True


class ImageConfig(BaseModel):
    repository: str = "ghcr.io/hardbyte/netchecks"
    pullPolicy: str = "IfNotPresent"
    tag: str = "main"


class Resources(BaseModel):
    claims: any = None
    limits: dict[str, str] | None = None
    requests: dict[str, str] | None = None


class ProbeConfig(BaseModel):
    imagePullSecrets: list[str] = []
    podAnnotations: dict[str, str] = {}
    image: ImageConfig = ImageConfig()
    resources: Resources | None = None
    verbose: bool = False  # Don't enable until the operator has been modified to split stdout and stderr


class Config(BaseSettings):
    probe: ProbeConfig = ProbeConfig()

    metrics: MetricsConfig = MetricsConfig()

    policy_report_max_results: int = 1000

    class Config:
        case_sensitive = True
        settings_environment_variable_name = "JSON_CONFIG"

        # Allow parsing of nested objects from environment variables
        # Ref: https://pydantic-docs.helpmanual.io/usage/settings/#parsing-environment-variable-values
        env_nested_delimiter = "__"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                json_config_settings_source,
                env_settings,
                file_secret_settings,
            )
