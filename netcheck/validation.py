import base64
import json
import logging
from typing import Dict

import celpy
import yaml
from celpy import CELParseError, CELEvalError, json_to_cel

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

    env = celpy.Environment()

    # Validate the CEL validation rule and compile to ast
    try:
        ast = env.compile(validation_rule)
    except CELParseError:
        print("Invalid CEL expression. Treating as error.")
        raise ValueError("Invalid CEL expression")

    # create the CEL program
    functions = {
        "parse_json": lambda s: json_to_cel(json.loads(s)),
        "parse_yaml": lambda s: json_to_cel(yaml.safe_load(s)),
        "b64decode": lambda s: base64.b64decode(s).decode("utf-8"),
        "b64encode": lambda s: base64.b64encode(s.encode()).decode(),
    }
    prgm = env.program(ast, functions=functions)

    # Set up the context
    activation = celpy.json_to_cel(context)

    # Evaluate the CEL expression
    try:
        context = prgm.evaluate(activation)
    except CELEvalError:
        # Note this can fail if the context is missing a key e.g. the probe
        # failed to return a value for a key that the validation rule expects

        return False

    return context
