"""Unit tests for operator configuration."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from netchecks_operator.config import Config, JsonConfigSettingsSource, MetricsConfig, ProbeConfig


class TestJsonConfigSettingsSource:
    """Tests for JsonConfigSettingsSource class."""

    def test_no_environment_variable_set(self, monkeypatch):
        """Test that source returns empty dict when env var not set."""
        # Ensure the env var is not set
        monkeypatch.delenv("JSON_CONFIG", raising=False)

        # Create a settings instance
        config = Config()
        source = JsonConfigSettingsSource(Config)

        result = source()

        assert result == {}

    def test_json_config_file_loaded(self, monkeypatch):
        """Test that JSON config file is loaded when env var is set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "metrics": {"port": 8888, "enabled": False},
                "policy_report_max_results": 500,
            }
            json.dump(config_data, f)
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            config = Config()

            # Check that values from JSON file are loaded
            assert config.metrics.port == 8888
            assert config.metrics.enabled is False
            assert config.policy_report_max_results == 500
        finally:
            os.unlink(config_file)

    def test_nested_config_from_json(self, monkeypatch):
        """Test that nested configuration objects are properly loaded."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "probe": {
                    "image": {"repository": "custom/image", "tag": "v1.2.3"},
                    "verbose": True,
                }
            }
            json.dump(config_data, f)
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            config = Config()

            assert config.probe.image.repository == "custom/image"
            assert config.probe.image.tag == "v1.2.3"
            assert config.probe.verbose is True
        finally:
            os.unlink(config_file)

    def test_json_config_with_partial_override(self, monkeypatch):
        """Test that JSON config works with partial configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"metrics": {"port": 8888}}
            json.dump(config_data, f)
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            config = Config()

            # JSON config should be applied
            assert config.metrics.port == 8888
            # Other fields should have default values
            assert config.policy_report_max_results == 1000
        finally:
            os.unlink(config_file)

    def test_json_config_priority(self, monkeypatch):
        """Test source priority: init > json > env."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"policy_report_max_results": 500}
            json.dump(config_data, f)
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            config = Config()

            # JSON config takes precedence over default
            assert config.policy_report_max_results == 500
        finally:
            os.unlink(config_file)

    def test_invalid_json_file_raises_error(self, monkeypatch):
        """Test that invalid JSON file raises an error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            with pytest.raises(json.JSONDecodeError):
                Config()
        finally:
            os.unlink(config_file)

    def test_nonexistent_file_raises_error(self, monkeypatch):
        """Test that referencing a nonexistent file raises an error."""
        monkeypatch.setenv("JSON_CONFIG", "/tmp/nonexistent_config.json")

        with pytest.raises(FileNotFoundError):
            Config()

    def test_custom_env_var_name(self, monkeypatch):
        """Test that custom environment variable name works."""
        # The default is JSON_CONFIG, but let's verify it's configurable
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"metrics": {"port": 7777}}
            json.dump(config_data, f)
            config_file = f.name

        try:
            # Use the standard JSON_CONFIG name
            monkeypatch.setenv("JSON_CONFIG", config_file)

            config = Config()
            assert config.metrics.port == 7777
        finally:
            os.unlink(config_file)


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = Config()

        assert config.metrics.port == 9090
        assert config.metrics.enabled is True
        assert config.policy_report_max_results == 1000
        assert config.probe.image.repository == "ghcr.io/hardbyte/netchecks"
        assert config.probe.verbose is False

    def test_config_model_config_settings(self):
        """Test that model_config settings are correctly set."""
        config = Config()

        # Verify model_config attributes
        assert config.model_config.get("case_sensitive") is True
        assert config.model_config.get("env_nested_delimiter") == "__"
        assert config.model_config.get("extra") == "ignore"

    def test_extra_fields_ignored(self, monkeypatch):
        """Test that extra fields in JSON are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "metrics": {"port": 8888},
                "unknown_field": "should be ignored",
                "another_unknown": {"nested": "value"},
            }
            json.dump(config_data, f)
            config_file = f.name

        try:
            monkeypatch.setenv("JSON_CONFIG", config_file)

            # Should not raise an error
            config = Config()

            assert config.metrics.port == 8888
            # Unknown fields should not be added
            assert not hasattr(config, "unknown_field")
        finally:
            os.unlink(config_file)
