import json
import logging

import click
import requests

from netcheck.dns import get_A_records_by_dns_lookup

logger = logging.getLogger("netcheck")

#logging.basicConfig(level=logging.DEBUG)

@click.group()
def cli():
    pass


@click.command()
@click.option('--config', help='Config file with netcheck assertions', type=click.File('r'))
def run(config):
    """Carry out all network assertions in given config file.
    """
    logger.info(f"Loading assertions from {config.name}")
    data = json.load(config)

    # TODO: Validate the config format

    click.echo(f"Loaded {len(data['assertions'])} assertions")

    # Run each test
    for test in data['assertions']:
        click.echo(f"Running test '{test['name']}'")
        for rule in test['rules']:
            check_individual_assertion(
                rule['type'],
                rule,
                should_fail=rule['expected'] != 'pass'
            )


@click.command()
@click.option('--server', default=None, help='DNS server to use for dns tests. E.g. 1.1.1.1')
@click.option('--host', default='github.com', help='Host to search for (DNS test)')
@click.option('--url', default='https://github.com/status', help='URL to request (http test)')
@click.option('--type', 'test_type', required=True, prompt='Test type (dns, http)', help='Type of test.')
@click.option('--should-fail/--should-pass', is_flag=True, default=False)
def check(test_type, server=None, host=None, url=None, should_fail=False):
    """Carry out a single network check"""

    test_config = {
        "server": server,
        "host": host,
        "url": url
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
            click.echo("Failed but was expected to pass")
            click.echo(test_detail)
        else:
            logging.debug("Failed. As expected.")

    else:
        if not should_fail:
            logging.debug("Passed. As expected.")
        else:
            click.echo("Passed but was expected to fail.")
            click.echo(test_detail)


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


cli.add_command(check)
cli.add_command(run)

if __name__ == '__main__':
    cli()
