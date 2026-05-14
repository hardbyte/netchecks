import datetime
import json
import logging
from typing import Dict


from netcheck.validation import evaluate_cel_with_context
from netcheck.version import OUTPUT_JSON_VERSION

from netcheck.version import NETCHECK_VERSION
from netcheck.checks.internal import internal_check
from netcheck.checks.dns import dns_lookup_check, DEFAULT_DNS_VALIDATION_RULE
from netcheck.checks.http import http_request_check, DEFAULT_HTTP_VALIDATION_RULE
from netcheck.checks.tcp import tcp_check, DEFAULT_TCP_VALIDATION_RULE
from netcheck.checks.postgres import (
    postgres_query_check,
    postgres_grants_check,
    DEFAULT_POSTGRES_VALIDATION_RULE,
    DEFAULT_POSTGRES_GRANTS_VALIDATION_RULE,
)
from netcheck.context import replace_template, LazyFileLoadingDict

logger = logging.getLogger("netcheck.runner")


def run_from_config(
    netchecks_config: Dict,
    err_console,
    verbose: bool = False,
    include_context: bool = False,
):
    if verbose:
        err_console.print(f"Loaded {len(netchecks_config['assertions'])} assertions")

    overall_results = {
        "type": "netcheck-output",
        "outputVersion": OUTPUT_JSON_VERSION,
        "metadata": {
            "creationTimestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "version": NETCHECK_VERSION,
        },
        "assertions": [],
    }

    # Load optional external contexts from the config
    context = {}
    for c in netchecks_config.get("contexts", []):
        if c["type"] == "file":
            # load the file at "path", parse it as JSON,
            # then add it to the context using its "name" as the key
            with open(c["path"], "r") as f:
                context[c["name"]] = json.load(f)
        elif c["type"] == "inline":
            # Inline contexts are processed for CEL templates
            inline_context = c["data"]
            inline_context = replace_template(inline_context, context)
            context[c["name"]] = inline_context
        elif c["type"] == "directory":
            # Return a Dict like object that lazy loads individual files
            # from the directory (with caching) and add them to the context
            context[c["name"]] = LazyFileLoadingDict(c["path"])
        else:
            logger.warning(f"Unknown context type '{c['type']}'")

    # Replace any template strings in the config
    netchecks_config = replace_template(netchecks_config, context)

    # Run each test
    for assertion in netchecks_config["assertions"]:
        assertion_results = []
        if verbose:
            err_console.print(f"Running tests for assertion '{assertion['name']}'")
        for rule in assertion["rules"]:
            result = check_individual_assertion(
                rule["type"],
                rule,
                err_console=err_console,
                validation_rule=rule.get("validation") or rule.get("validate", {}).get("pattern"),
                validation_context=context,
                verbose=verbose,
                include_context=include_context,
            )
            assertion_results.append(result)

        overall_results["assertions"].append({"name": assertion["name"], "results": assertion_results})

    return overall_results


def check_individual_assertion(
    test_type: str,
    test_config,
    err_console,
    validation_rule=None,
    validation_context=None,
    verbose=False,
    include_context=False,
):
    match test_type:
        case "dns":
            if verbose:
                err_console.print(f"DNS check looking up host '{test_config['host']}'")
            test_detail = dns_lookup_check(
                host=test_config["host"],
                server=test_config.get("server"),
                timeout=test_config.get("timeout"),
                source_ip=test_config.get("source-ip"),
            )
        case "http":
            if verbose:
                err_console.print(f"http check with url '{test_config['url']}'")
            test_detail = http_request_check(
                test_config["url"],
                test_config.get("method", "get").lower(),
                headers=test_config.get("headers"),
                timeout=test_config.get("timeout"),
                verify=test_config.get("verify-tls-cert", True),
                source_ip=test_config.get("source-ip"),
            )
        case "tcp":
            if verbose:
                err_console.print(f"TCP check connecting to {test_config['host']}:{test_config['port']}")
            test_detail = tcp_check(
                host=test_config["host"],
                port=int(test_config["port"]),
                timeout=test_config.get("timeout", 5),
                source_ip=test_config.get("source-ip"),
            )
        case "internal":
            if verbose:
                err_console.print(f"Internal check with command '{test_config['command']}'")
            test_detail = internal_check(
                test_config.get("timeout", 5),
            )
        case "postgres":
            if verbose:
                err_console.print("Postgres check running SQL statement")
            test_detail = postgres_query_check(
                dsn=test_config["dsn"],
                query=test_config["query"],
                params=test_config.get("params"),
                timeout=test_config.get("timeout", 5),
                read_only=test_config.get("read-only", True),
                rollback=test_config.get("rollback", True),
                row_limit=test_config.get("row-limit", 100),
            )
        case "postgres-grants":
            if verbose:
                err_console.print("Postgres grants check evaluating effective privileges")
            test_detail = postgres_grants_check(
                dsn=test_config["dsn"],
                rules=test_config.get("rules", []),
                timeout=test_config.get("timeout", 5),
            )
        case _:
            logger.warning("Unhandled test type")
            raise NotImplementedError("Unknown test type")

    if "name" in test_config:
        test_detail["name"] = test_config["name"]

    if validation_rule is None:
        # use the default validation rule
        match test_type:
            case "http":
                validation_rule = DEFAULT_HTTP_VALIDATION_RULE
            case "dns":
                validation_rule = DEFAULT_DNS_VALIDATION_RULE
            case "tcp":
                validation_rule = DEFAULT_TCP_VALIDATION_RULE
            case "internal":
                validation_rule = "true"
            case "postgres":
                validation_rule = DEFAULT_POSTGRES_VALIDATION_RULE
            case "postgres-grants":
                validation_rule = DEFAULT_POSTGRES_GRANTS_VALIDATION_RULE
            case _:
                raise NotImplementedError("Unknown check type")
    elif verbose:
        err_console.print("Using custom validation rule")

    test_detail["spec"]["pattern"] = validation_rule

    logger.info(f"Validating probe result with rule: {validation_rule}")
    logger.info(f"Probe result: {test_detail}")
    if validation_context is not None:
        if "data" in validation_context or "spec" in validation_context:
            raise ValueError("validation_context cannot contain a 'data' or 'spec' key")
        test_detail.update(validation_context)

    passed = evaluate_cel_with_context(test_detail, validation_rule)

    # Remove the context from the `test_detail` object
    if not include_context and validation_context is not None:
        for key in validation_context:
            if key in test_detail:
                del test_detail[key]

    # Strip out known sensitive fields
    if not include_context:
        for field in {"headers", "dsn", "password", "params", "connection"}:
            if field in test_detail["spec"]:
                test_detail["spec"][field] = "REDACTED"
            if field in test_detail["data"]:
                test_detail["data"][field] = "REDACTED"

    # Add the pass/status to the individual result. We also support an "expected": "fail" option
    # which will cause the test to fail if the validation passes.
    if test_config.get("expected") == "fail":
        test_detail["status"] = "fail" if passed else "pass"
    else:
        test_detail["status"] = "pass" if passed else "fail"

    return test_detail
