import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from structlog import get_logger

logger = get_logger()


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A simple settings source that loads variables from a JSON file
    pointed at by an environment variable.

    The environment variable name is loaded from the default config.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Not used for our implementation — we override __call__ directly
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        settings_environment_variable_name = self.settings_cls.model_config.get(
            "settings_environment_variable_name", "JSON_CONFIG"
        )

        if settings_environment_variable_name in os.environ:
            config_file_path = Path(os.environ.get(settings_environment_variable_name))
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
    claims: Any = None
    limits: dict[str, str] | None = None
    requests: dict[str, str] | None = None


class ProbeConfig(BaseModel):
    imagePullSecrets: list[str] = []
    podAnnotations: dict[str, str] = {}
    image: ImageConfig = ImageConfig()
    resources: Resources | None = None
    tolerations: list[dict] | None = None
    affinity: dict[str, dict] | None = None

    verbose: bool = False  # Don't enable until the operator has been modified to split stdout and stderr


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_nested_delimiter="__",
        extra="ignore",
        # Custom attribute for our json config source
        settings_environment_variable_name="JSON_CONFIG",
    )

    probe: ProbeConfig = ProbeConfig()
    metrics: MetricsConfig = MetricsConfig()
    policy_report_max_results: int = 1000

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls),
            env_settings,
            file_secret_settings,
        )
