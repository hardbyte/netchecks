import json
import logging
from enum import Enum
from pathlib import Path

import typer
import requests

from netcheck.dns import get_A_records_by_dns_lookup

app = typer.Typer()
logger = logging.getLogger("netcheck")
#logging.basicConfig(level=logging.DEBUG)


@app.command()
def run(
        config: Path = typer.Option(..., exists=True, file_okay=True, help='Config file with netcheck assertions')
        ):
    """Carry out all network assertions in given config file.
    """
    logger.info(f"Loading assertions from {config}")
    with config.open() as f:
        data = json.load(f)

    # TODO: Validate the config format

    print(f"Loaded {len(data['assertions'])} assertions")

    # Run each test
    for test in data['assertions']:
        print(f"Running test '{test['name']}'")
        for rule in test['rules']:
            check_individual_assertion(
                rule['type'],
                rule,
                should_fail=rule['expected'] != 'pass'
            )





class NetcheckHttpMethod(str, Enum):
    get = 'get'
    post = 'post'
    patch = 'patch'
    put = 'put'
    delete = 'delete'


class NetcheckTestType(str, Enum):
    dns = "dns"
    http = 'http'


@app.command()
def check(
        test_type: NetcheckTestType = typer.Argument(..., help='Test type'),
        server: str = typer.Option(None, help="DNS server to use for dns tests.", rich_help_panel="dns test"),
        host: str = typer.Option('github.com', help='Host to search for', rich_help_panel="dns test"),
        url: str = typer.Option('https://github.com/status', help="URL to request", rich_help_panel="http test"),
        method: NetcheckHttpMethod = typer.Option(NetcheckHttpMethod.get, help="HTTP method", rich_help_panel='http test'),
        should_fail: bool = typer.Option(False, "--should-fail/--should-pass")
):
    """Carry out a single network check"""

    test_config = {
        "server": server,
        "host": host,
        "url": url,
        'method': method
    }

    check_individual_assertion(test_type, test_config, should_fail)


def check_individual_assertion(test_type, test_config, should_fail):
    match test_type:
        case 'dns':
            logging.debug(f"DNS check with nameserver {test_config['server']} and {test_config['host']}")
            failed, test_detail = dns_lookup_check(test_config['host'], test_config['server'])
        case 'http':
            failed, test_detail = get_request_check(test_config['url'])
        case _:
            logger.warning("Unhandled test type")
            raise NotImplemented("Unknown test type")
    notify_for_unexpected_test_result(failed, should_fail, test_detail)


def notify_for_unexpected_test_result(failed, should_fail, test_detail):
    if failed:
        if not should_fail:
            logger.warning("Failed but was expected to pass")
            print(test_detail)
        else:
            logging.debug("Failed. As expected.")

    else:
        if not should_fail:
            logging.debug("Passed. As expected.")
        else:
            logger.warning("Passed but was expected to fail.")
            print(test_detail)


def get_request_check(url):
    failed = False
    details = {
        'type': 'http',
        'method': "GET",
        'url': url,

    }
    try:
        response = requests.get(url, timeout=30)
        details['status-code'] = response.status_code
    except Exception as e:
        failed = True

    return failed, details


def dns_lookup_check(host, server):
    failed = False
    detail = {
        'type': 'dns',
        'nameserver': server,
        'host': host
    }
    try:
        ip_addresses = get_A_records_by_dns_lookup(host, nameserver=server)
        detail['A'] = ip_addresses
    except Exception as e:
        failed = True
    return failed, detail


if __name__ == '__main__':
    app()
