import json
import logging
from typing import Dict

import celpy
from celpy import CELParseError, CELEvalError, json_to_cel

logger = logging.getLogger("netcheck.validation")

def validate_probe_result(result: Dict, validation_rule: str):
    logger.info(f"Validating probe result with rule: {validation_rule}")
    logger.info(f"Probe result: {result}")

    env = celpy.Environment()

    # Validate the CEL validation rule and compile to ast
    try:
        ast = env.compile(validation_rule)
    except CELParseError as e:
        print("Invalid CEL expression. Treating as error.")
        raise

    # create the CEL program
    functions = {
        "parse_json": lambda s: json_to_cel(json.loads(s)),
    }
    prgm = env.program(ast, functions=functions)

    # Set up the context
    activation = celpy.json_to_cel(result)

    # Evaluate the CEL expression
    try:
        result = prgm.evaluate(activation)
    except CELEvalError as e:
        # Note this can fail if the context is missing a key e.g. the probe
        # failed to return a value for a key that the validation rule expects

        return False

    return result
