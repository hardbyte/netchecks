"""Unit tests for context loading and LazyFileLoadingDict."""

import os
import tempfile
import pytest
from pathlib import Path

from netcheck.context import LazyFileLoadingDict, replace_template_in_string, replace_template


class TestLazyFileLoadingDict:
    """Tests for LazyFileLoadingDict class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "secret1.txt").write_text("secret-value-1")
            Path(tmpdir, "secret2.txt").write_text("secret-value-2")
            Path(tmpdir, "config.json").write_text('{"key": "value"}')
            yield tmpdir

    def test_lazy_loading_basic(self, temp_dir):
        """Test basic lazy loading of files."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        # Check that keys are pre-populated
        assert "secret1.txt" in lazy_dict
        assert "secret2.txt" in lazy_dict
        assert "config.json" in lazy_dict

        # Values should be None initially (lazy loading)
        # Access the underlying dict to check without triggering lazy loading
        assert dict.__getitem__(lazy_dict, "secret1.txt") is None

        # Accessing a value should load the file
        assert lazy_dict["secret1.txt"] == "secret-value-1"

        # Value should now be cached
        assert dict.__getitem__(lazy_dict, "secret1.txt") == "secret-value-1"

    def test_lazy_loading_multiple_access(self, temp_dir):
        """Test that files are only loaded once (caching)."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        # Access the same file multiple times
        value1 = lazy_dict["secret2.txt"]
        value2 = lazy_dict["secret2.txt"]

        assert value1 == value2 == "secret-value-2"

    def test_items_forces_loading(self, temp_dir):
        """Test that items() forces loading of all files."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        items = list(lazy_dict.items())

        # All files should be loaded
        assert ("secret1.txt", "secret-value-1") in items
        assert ("secret2.txt", "secret-value-2") in items
        assert ("config.json", '{"key": "value"}') in items

    def test_materialize(self, temp_dir):
        """Test materialize() converts to regular dict."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        # Materialize should return a regular dict
        regular_dict = lazy_dict.materialize()

        # Check type
        assert type(regular_dict) is dict
        assert not isinstance(regular_dict, LazyFileLoadingDict)

        # Check contents
        assert regular_dict["secret1.txt"] == "secret-value-1"
        assert regular_dict["secret2.txt"] == "secret-value-2"
        assert regular_dict["config.json"] == '{"key": "value"}'

    def test_materialize_with_cel(self, temp_dir):
        """Test that materialized dict works with CEL evaluation."""
        from cel import cel

        lazy_dict = LazyFileLoadingDict(temp_dir)
        regular_dict = lazy_dict.materialize()

        # Test CEL can access the materialized dict
        context = {"data": regular_dict}
        env = cel.Context(variables=context)
        result = cel.evaluate('data["secret1.txt"]', env)

        assert result == "secret-value-1"

    def test_empty_directory(self):
        """Test LazyFileLoadingDict with an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lazy_dict = LazyFileLoadingDict(tmpdir)

            assert len(lazy_dict) == 0
            assert list(lazy_dict.items()) == []
            assert lazy_dict.materialize() == {}

    def test_nonexistent_key(self, temp_dir):
        """Test accessing a non-existent key raises KeyError."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        with pytest.raises(KeyError):
            _ = lazy_dict["nonexistent.txt"]

    def test_path_traversal_protection(self, temp_dir):
        """Test that path traversal attempts are prevented."""
        lazy_dict = LazyFileLoadingDict(temp_dir)

        # Try to inject a path traversal key
        # This should not exist in the dict since it wasn't in os.listdir
        assert "../etc/passwd" not in lazy_dict

        # Even if we try to manually set it, it should be blocked
        with pytest.raises(KeyError):
            _ = lazy_dict["../etc/passwd"]

    def test_subdirectories_ignored(self, temp_dir):
        """Test that subdirectories are not loaded as files."""
        # Create a subdirectory
        subdir = Path(temp_dir, "subdir")
        subdir.mkdir()

        lazy_dict = LazyFileLoadingDict(temp_dir)

        # Subdirectory should be in keys (from os.listdir)
        assert "subdir" in lazy_dict

        # But trying to access it should keep it as None (not a file)
        # The __getitem__ checks os.path.isfile()
        assert lazy_dict["subdir"] is None


class TestTemplateReplacement:
    """Tests for template replacement functions."""

    def test_replace_template_in_string_with_dict_context(self):
        """Test template replacement with regular dict context."""
        context = {"api": {"token": "secret123"}}
        template_str = "Authorization: Bearer {{ api.token }}"

        result = replace_template_in_string(template_str, context)

        assert result == "Authorization: Bearer secret123"

    def test_replace_template_nested(self):
        """Test template replacement in nested dicts."""
        context = {"secret": "value123"}
        config = {
            "headers": {
                "X-API-Key": "{{ secret }}"
            }
        }

        result = replace_template(config, context)

        assert result["headers"]["X-API-Key"] == "value123"

    def test_replace_template_in_list(self):
        """Test template replacement in lists."""
        context = {"item": "test"}
        config = {
            "items": ["{{ item }}", "static", "{{ item }}"]
        }

        result = replace_template(config, context)

        assert result["items"] == ["test", "static", "test"]
