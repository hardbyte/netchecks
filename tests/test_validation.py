"""Unit tests for CEL validation and error handling."""

import pytest

from netcheck.validation import evaluate_cel_with_context


class TestCELValidation:
    """Tests for CEL expression validation."""

    def test_valid_expression_passes(self):
        """Test that a valid passing expression returns True."""
        context = {"status": 200}
        result = evaluate_cel_with_context(context, "status == 200")
        assert result is True

    def test_valid_expression_fails(self):
        """Test that a valid failing expression returns False."""
        context = {"status": 404}
        result = evaluate_cel_with_context(context, "status == 200")
        assert result is False

    def test_complex_expression(self):
        """Test complex CEL expressions work correctly."""
        context = {
            "data": {"status-code": 200, "body": '{"result": "ok"}'},
            "spec": {"url": "https://example.com"},
        }
        result = evaluate_cel_with_context(
            context, "data['status-code'] == 200 && parse_json(data.body).result == 'ok'"
        )
        assert result is True

    def test_invalid_syntax_raises_value_error(self):
        """Test that invalid CEL syntax raises ValueError, not returning False."""
        context = {"status": 200}

        # Invalid syntax should raise ValueError to surface configuration errors
        with pytest.raises(ValueError, match="Invalid CEL expression"):
            evaluate_cel_with_context(context, "invalid syntax +++")

    def test_multiple_invalid_syntax_patterns(self):
        """Test various invalid syntax patterns all raise ValueError."""
        context = {"status": 200}

        invalid_expressions = [
            "status ==",  # Incomplete comparison
            "status 200",  # Missing operator
            "== 200",  # Missing left operand
            "status & 200",  # Single & instead of &&
            "status | 200",  # Single | instead of ||
        ]

        for expr in invalid_expressions:
            with pytest.raises(ValueError, match="Invalid CEL expression"):
                evaluate_cel_with_context(context, expr)

    def test_runtime_error_returns_false(self):
        """Test that runtime errors (missing variables) return False, not raise."""
        context = {}

        # Missing variable should return False (validation fails gracefully)
        result = evaluate_cel_with_context(context, "data.missing == 'value'")
        assert result is False

    def test_type_error_returns_false(self):
        """Test that type errors return False."""
        context = {"value": "string"}

        # Type error (comparing string to int) should return False
        result = evaluate_cel_with_context(context, "value > 100")
        assert result is False

    def test_custom_functions(self):
        """Test that custom functions (parse_json, parse_yaml, etc.) work."""
        context = {"json_str": '{"key": "value"}'}

        result = evaluate_cel_with_context(context, "parse_json(json_str).key == 'value'")
        assert result is True

    def test_base64_functions(self):
        """Test base64 encode/decode functions."""
        import base64

        context = {"plaintext": "hello world"}
        encoded = base64.b64encode(b"hello world").decode()

        # Test b64encode
        result = evaluate_cel_with_context(context, f"b64encode(plaintext) == '{encoded}'")
        assert result is True

        # Test b64decode
        context2 = {"encoded": encoded}
        result2 = evaluate_cel_with_context(context2, "b64decode(encoded) == 'hello world'")
        assert result2 is True

    def test_yaml_parsing(self):
        """Test YAML parsing function."""
        context = {"yaml_str": "key: value\nlist:\n  - item1\n  - item2"}

        result = evaluate_cel_with_context(context, "parse_yaml(yaml_str).key == 'value'")
        assert result is True

        result2 = evaluate_cel_with_context(context, "size(parse_yaml(yaml_str).list) == 2")
        assert result2 is True
