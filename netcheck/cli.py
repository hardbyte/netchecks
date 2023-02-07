import json
import logging
from enum import Enum
from pathlib import Path
from rich import print_json
from rich.console import Console
import typer
from typing import List, Optional
import urllib3

from netcheck.version import NETCHECK_VERSION, OUTPUT_JSON_VERSION
from netcheck.http import NetcheckHttpMethod
from netcheck.runner import run_from_config, check_individual_assertion




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

def show_version(value: bool = True):
    """Print netcheck version"""
    if value:
        typer.echo(f"Netcheck version {NETCHECK_VERSION}")
        raise typer.Exit()

@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", callback=show_version, is_eager=True),
):
    pass


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

    # TODO: Validate the config format once stable
    overall_results = run_from_config(data, err_console, verbose)

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
        headers: Optional[List[str]] = typer.Option(
            None,
            '-h',
            '--header',
            help="Headers to send with request. Format: 'key:value'"),
        verbose: bool = typer.Option(False, '-v', '--verbose')
):
    """Carry out a http network check"""
    parsed_headers = {}
    for h in headers:
        if ":" in h:
            key, value = h.split(':')
            parsed_headers[key.strip()] = value.strip()

    test_config = {
        "url": url,
        'method': method,
        'timeout': timeout,
        'headers': parsed_headers
    }

    if verbose:

        err_console.print(f"Netcheck http configuration:")
        err_console.print_json(data=test_config)

    result = check_individual_assertion(
        NetcheckTestType.http,
        test_config,
        should_fail,
        err_console,
        verbose=verbose
    )
    failed = result['status'] in {'fail', 'error'}
    notify_for_unexpected_test_result(failed, should_fail, verbose=verbose)
    print_json(data=result)


@app.command()
def dns(
        server: str = typer.Option(None, help="DNS server to use for dns tests.", rich_help_panel="dns test"),
        host: str = typer.Option('github.com', help='Host to search for', rich_help_panel="dns test"),
        should_fail: bool = typer.Option(False, "--should-fail/--should-pass"),
        timeout: float = typer.Option(30.0, '-t', '--timeout', help='Timeout in seconds'),
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
        err_console,
        verbose=verbose
    )

    failed = result['status'] in {'fail', 'error'}
    notify_for_unexpected_test_result(failed, should_fail, verbose=verbose)
    # Currently always output JSON to stdout
    print_json(data=result)


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


if __name__ == '__main__':
    app()
