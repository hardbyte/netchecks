import base64
import json
import logging
from typing import Dict
import yaml

from cel import cel


logger = logging.getLogger("netcheck.validation")


def evaluate_cel_with_context(context: Dict, validation_rule: str):
    """
    Evaluates a Common Expression Language (CEL) validation rule with a given context.

    This function compiles the CEL validation rule into an Abstract Syntax Tree (AST),
    creates a CEL program with additional functions (parse_json), sets up the context, and then
    evaluates the CEL expression. If the evaluation fails due to a missing key in the
    context, the function returns False.

    Args:
        context: A dictionary representing the context in which the validation rule
            is evaluated. The context should be in a format that can be converted to CEL.
        validation_rule: A CEL validation rule to be evaluated.

    Returns:
        Any: The result of the CEL expression evaluation. If the evaluation fails due to a
            missing key in the context, the function returns False.

    Raises:
        ValueError: If the CEL expression is invalid.
    """
    functions = {
        "parse_json": lambda s: json.loads(s),
        "parse_yaml": lambda s: yaml.safe_load(s),
        "b64decode": lambda s: base64.b64decode(s).decode("utf-8"),
        "b64encode": lambda s: base64.b64encode(s.encode()).decode(),
    }
    env = cel.Context(
        variables=context,
        functions=functions,
    )

    # Evaluate the CEL expression
    try:
        result = cel.evaluate(validation_rule, env)
    except ValueError as e:
        error_msg = str(e)
        # Distinguish between parse errors (config bugs) and execution errors (validation failures)
        if "Failed to parse" in error_msg:
            # Parse/syntax errors indicate invalid CEL configuration - raise to surface
            logger.error(f"Invalid CEL expression syntax: {e}")
            raise ValueError(f"Invalid CEL expression: {e}") from e
        else:
            # Execution errors (type mismatches, etc.) indicate validation failure
            # These can happen with valid expressions that fail at runtime
            logger.debug(f"CEL execution failed: {e}")
            return False
    except RuntimeError as e:
        # Runtime errors (undefined variables) indicate validation failure
        # This can happen if the probe failed to return expected values
        logger.debug(f"CEL evaluation failed: {e}")
        return False

    return result
