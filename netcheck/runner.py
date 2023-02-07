import datetime
import logging
from typing import Dict

from netcheck.version import OUTPUT_JSON_VERSION

from netcheck.version import NETCHECK_VERSION
from netcheck.dns import dns_lookup_check
from netcheck.http import http_request_check


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
                should_fail=rule.get('expected', 'pass') != 'pass',
                err_console=err_console,
                verbose=verbose,
            )
            assertion_results.append(result)

        overall_results['assertions'].append({
            'name': assertion['name'],
            'results': assertion_results
        })
    return overall_results


def check_individual_assertion(test_type: str, test_config, should_fail, err_console, verbose=False):
    match test_type:
        case 'dns':
            if verbose:
                err_console.print(f"DNS check looking up host '{test_config['host']}'")
            test_detail = dns_lookup_check(
                host=test_config['host'],
                server=test_config.get('server'),
                timeout=test_config.get('timeout'),
                should_fail=should_fail,
            )
        case 'http':
            if verbose:
                err_console.print(f"http check with url '{test_config['url']}'")
            test_detail = http_request_check(
                test_config['url'],
                test_config.get('method', 'get'),
                headers=test_config.get('headers'),
                timeout=test_config.get('timeout'),
                verify=test_config.get('verify-tls-cert', True),
                should_fail=should_fail,
            )
        case _:
            logger.warning("Unhandled test type")
            raise NotImplemented("Unknown test type")

    return test_detail
