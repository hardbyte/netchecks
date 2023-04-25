import datetime
import logging
from typing import Dict

from netcheck.validation import validate_probe_result
from netcheck.version import OUTPUT_JSON_VERSION

from netcheck.version import NETCHECK_VERSION
from netcheck.dns import dns_lookup_check, DEFAULT_DNS_VALIDATION_RULE
from netcheck.http import http_request_check, DEFAULT_HTTP_VALIDATION_RULE

logger = logging.getLogger("netcheck.runner")


def run_from_config(netchecks_config: Dict, err_console, verbose: bool = False):
    if verbose:
        err_console.print(f"Loaded {len(netchecks_config['assertions'])} assertions")
    overall_results = {
        'type': 'netcheck-output',
        'outputVersion': OUTPUT_JSON_VERSION,
        'metadata': {
            'creationTimestamp': datetime.datetime.utcnow().isoformat(),
            'version': NETCHECK_VERSION,
        },
        'assertions': []
    }
    # Run each test
    for assertion in netchecks_config['assertions']:
        assertion_results = []
        if verbose:
            err_console.print(f"Running tests for assertion '{assertion['name']}'")
        for rule in assertion['rules']:
            result = check_individual_assertion(
                rule['type'],
                rule,
                err_console=err_console,
                validation_rule=rule.get('validation'),
                verbose=verbose,
            )
            assertion_results.append(result)

        overall_results['assertions'].append({
            'name': assertion['name'],
            'results': assertion_results
        })
    return overall_results


def check_individual_assertion(test_type: str, test_config, err_console, validation_rule=None, verbose=False):
    match test_type:

        case 'dns':
            if verbose:
                err_console.print(f"DNS check looking up host '{test_config['host']}'")
            test_detail = dns_lookup_check(
                host=test_config['host'],
                server=test_config.get('server'),
                timeout=test_config.get('timeout'),

            )
        case 'http':
            if verbose:
                err_console.print(f"http check with url '{test_config['url']}'")
            test_detail = http_request_check(
                test_config['url'],
                test_config.get('method', 'get').lower(),
                headers=test_config.get('headers'),
                timeout=test_config.get('timeout'),
                verify=test_config.get('verify-tls-cert', True),

            )
        case _:
            logger.warning("Unhandled test type")
            raise NotImplemented("Unknown test type")

    if validation_rule is None:
        # use the default validation rule
        match test_type:
            case 'http': validation_rule = DEFAULT_HTTP_VALIDATION_RULE
            case 'dns': validation_rule = DEFAULT_DNS_VALIDATION_RULE
    elif verbose:
        err_console.print("Using custom validation rule")

    test_detail['spec']['pattern'] = validation_rule
    passed = validate_probe_result(test_detail, validation_rule)

    # Add the pass/status to the individual result. We also support an "expected": "fail" option
    # which will cause the test to fail if the validation passes.
    if test_config.get('expected') == 'fail':
        test_detail['status'] = 'fail' if passed else 'pass'
    else:
        test_detail['status'] = 'pass' if passed else 'fail'

    return test_detail
