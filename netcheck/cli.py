import datetime
import json
import logging
from enum import Enum
from pathlib import Path
from rich import print_json
from rich.console import Console
import typer
from pydantic import BaseModel, Field
import requests
from typing import Optional
import urllib3
import pkg_resources
from netcheck.dns import get_A_records_by_dns_lookup
from netcheck.http import NetcheckHttpMethod, http_request_check

try:
    NETCHECK_VERSION = pkg_resources.get_distribution('netcheck').version
except pkg_resources.DistributionNotFound:
    NETCHECK_VERSION = 'unknown'

OUTPUT_JSON_VERSION = 'dev' #set to v1 once stable

app = typer.Typer()
logger = logging.getLogger("netcheck")
#logging.basicConfig(level=logging.DEBUG)
logging.captureWarnings(True)

err_console = Console(stderr=True)

# We disable urllib warning because we expect to be carrying out tests against hosts using self-signed
# certs etc.
urllib3.disable_warnings()


class NetcheckOutputType(str, Enum):
    json = 'json'


class NetcheckTestType(str, Enum):
    dns = "dns"
    http = 'http'


@app.command()
def run(
        config: Path = typer.Option(..., exists=True, file_okay=True,
                                    help='Config file with netcheck assertions'),
        output: Optional[NetcheckOutputType] = typer.Option(NetcheckOutputType.json,
                                                            '-o',
                                                            '--output',
                                                            help="Output format"),
        verbose: bool = typer.Option(False, '-v')
        ):
    """Carry out all network assertions in given config file.
    """
    if verbose:
        err_console.print(f"Loading assertions from {config}")
    with config.open() as f:
        data = json.load(f)

    # TODO: Validate the config format
    if verbose:
        err_console.print(f"Loaded {len(data['assertions'])} assertions")

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
    for assertion in data['assertions']:
        assertion_results = []
        if verbose:
            err_console.print(f"Running tests for assertion '{assertion['name']}'")
        for rule in assertion['rules']:
            result = check_individual_assertion(
                rule['type'],
                rule,
                should_fail=rule['expected'] != 'pass',
                verbose=verbose,
            )
            assertion_results.append(result)

        overall_results['assertions'].append({
            'name': assertion['name'],
            'results': assertion_results
        })

    # TODO summary output

    if verbose:
        err_console.print(f"Output type {output}")

    print_json(data=overall_results)


@app.command()
def http(
        url: str = typer.Option('https://github.com/status', help="URL to request", rich_help_panel="http test"),
        method: NetcheckHttpMethod = typer.Option(NetcheckHttpMethod.get,
                                                  help="HTTP method",
                                                  rich_help_panel='http test'),
        timeout: float = typer.Option(30.0, '-t', '--timeout', help='Timeout in seconds'),
        should_fail: bool = typer.Option(False, "--should-fail/--should-pass"),
        output: Optional[NetcheckOutputType] = typer.Option(
            NetcheckOutputType.json,
            '-o',
            '--output',
            help="Output format"),
        verbose: bool = typer.Option(False, '-v', '--verbose')
):
    """Carry out a http network check"""

    test_config = {
        "url": url,
        'method': method,
        'timeout': timeout
    }

    if verbose:
        err_console.print(f"netcheck http")
        err_console.print(f"Options")
        err_console.print_json(data=test_config)

    result = check_individual_assertion(
        NetcheckTestType.http,
        test_config,
        should_fail,
        verbose=verbose
    )
    print_json(data=result)


@app.command()
def dns(
        server: str = typer.Option(None, help="DNS server to use for dns tests.", rich_help_panel="dns test"),
        host: str = typer.Option('github.com', help='Host to search for', rich_help_panel="dns test"),
        should_fail: bool = typer.Option(False, "--should-fail/--should-pass"),
        timeout: float = typer.Option(30.0, '-t', '--timeout', help='Timeout in seconds'),
        output: Optional[NetcheckOutputType] = typer.Option(
            NetcheckOutputType.json,
            '-o',
            '--output',
            help="Output format"),
        verbose: bool = typer.Option(False, '-v', '--verbose')
):
    """Carry out a dns check"""

    test_config = {
        "server": server,
        "host": host,
        "timeout": timeout,
    }
    if verbose:
        err_console.print(f"netcheck dns")
        err_console.print(f"Options")
        err_console.print_json(data=test_config)

    result = check_individual_assertion(
        NetcheckTestType.dns,
        test_config,
        should_fail,
        verbose=verbose
    )

    # Currently always output JSON to stdout
    print_json(data=result)


def check_individual_assertion(test_type: str, test_config, should_fail, verbose=False):
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
                headers=test_config.get('headers', []),
                timeout=test_config.get('timeout'),
                verify=test_config.get('verify-tls-cert', True),
                should_fail=should_fail,
            )
        case _:
            logger.warning("Unhandled test type")
            raise NotImplemented("Unknown test type")
    failed = test_detail['status'] in {'fail', 'error'}
    notify_for_unexpected_test_result(failed, should_fail, verbose=verbose)

    return test_detail


def notify_for_unexpected_test_result(failed, should_fail, verbose=False):
    if verbose:
        if failed:
            if not should_fail:
                err_console.print("[bold red]:boom: Failed but was expected to pass[/]")
            else:
                err_console.print("[yellow]:cross_mark: Failed. As expected.[/]")
        else:
            if not should_fail:
                err_console.print("[green]✔ Passed (as expected)[/]")
            else:
                err_console.print("[bold red]:bomb: The network test worked but was expected to fail![/]")


def dns_lookup_check(host, server, timeout=10, should_fail=False):

    test_spec = {
        'type': 'dns',
        'shouldFail': should_fail,
        'nameserver': server,
        'host': host,
        'timeout': timeout,
    }
    result_data = {
        'startTimestamp': datetime.datetime.utcnow().isoformat(),
    }

    output = {
        'status': 'error',
        'spec': test_spec,
        'data': result_data
    }

    try:
        ip_addresses = get_A_records_by_dns_lookup(host, nameserver=server, timeout=timeout)
        result_data['A'] = ip_addresses
        output['status'] = 'pass' if not should_fail else 'fail'
    except Exception as e:
        logger.info(f"Caught exception:\n\n{e}")
        output['status'] = 'pass' if should_fail else 'fail'
        result_data['exception-type'] = e.__class__.__name__
        result_data['exception'] = str(e)

    result_data['endTimestamp'] = datetime.datetime.utcnow().isoformat()

    return output


if __name__ == '__main__':
    app()
