import json

import pytest
from typer.testing import CliRunner

from netcheck.cli import app

runner = CliRunner(mix_stderr=False)


# To write the stderr and stdout to separate files use:
# poetry run netcheck http -v 2> errlog > stdout


def test_invalid_command():
    result = runner.invoke(app, ["unknown"])
    assert result.exit_code != 0


def test_default_dns_check():
    result = runner.invoke(app, ["dns"])
    assert result.exit_code == 0
    assert len(result.stderr) == 0
    data = result.stdout
    json.loads(data)


def test_verbose_default_dns_check():
    result = runner.invoke(app, ["dns", "-v"])
    assert result.exit_code == 0
    assert "DNS" in result.stderr
    assert "Passed" in result.stderr
    assert "github.com" in result.stderr
    data = result.stdout
    json.loads(data)


def test_dns_check_with_custom_validation():
    result = runner.invoke(
        app,
        [
            "dns",
            "--validation-rule",
            "data.canonical_name == 'github.com.' && data.response.contains('NOERROR') && size(data.A)>=1",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)

    assert data["status"] == "pass"


def test_failing_dns_check_with_custom_validation():
    result = runner.invoke(
        app,
        [
            "dns",
            "--validation-rule",
            "data.canonical_name == 'github.com.' && size(data.A)==0",
        ],
    )
    assert result.exit_code == 0
    print(result.stdout)
    data = json.loads(result.stdout)

    assert data["status"] == "fail"


def test_default_http_check():
    result = runner.invoke(app, ["http"])
    assert result.exit_code == 0
    assert len(result.stderr) == 0
    data = json.loads(result.stdout)
    assert data["status"] == "pass"


def test_verbose_default_http_check():
    result = runner.invoke(app, ["http", "-v"])
    assert result.exit_code == 0
    assert "http" in result.stderr
    assert "Passed" in result.stderr
    assert "github.com/status" in result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "pass"


def test_default_http_check_should_fail():
    result = runner.invoke(app, ["http", "--should-fail"])
    assert result.exit_code == 0

    data = json.loads(result.stdout)
    assert data["status"] == "fail"


def test_http_check_with_timout():
    result = runner.invoke(
        app, ["http", "--timeout", "2.1", "--url", "https://pie.dev/status/200"]
    )
    assert result.exit_code == 0

    data = result.stdout
    payload = json.loads(data)
    assert payload["spec"]["timeout"] == 2.1


def test_http_check_with_headers():
    result = runner.invoke(
        app,
        ["http", "--url", "https://pie.dev/headers", "--header", "X-Test-Header: test"],
    )
    assert result.exit_code == 0, result.stderr

    data = result.stdout
    payload = json.loads(data)
    assert payload["spec"]["headers"]["X-Test-Header"] == "test"
    assert "X-Test-Header" in json.loads(payload["data"]["body"])["headers"]


def test_http_check_with_custom_validation_passing():
    result = runner.invoke(
        app,
        [
            "http",
            "--url",
            "https://pie.dev/headers",
            "--header",
            "X-Test-Header: test",
            "--validation-rule",
            "data.body.contains('X-Test-Header') && data['status-code'] == 200",
        ],
    )
    assert result.exit_code == 0, result.stderr

    data = result.stdout
    payload = json.loads(data)
    assert payload["status"] == "pass"


def test_http_check_with_custom_validation_failing():
    result = runner.invoke(
        app,
        [
            "http",
            "--url",
            "https://pie.dev/headers",
            "--header",
            "X-Test-Header: test",
            "--validation-rule",
            "data.body.contains('missing') && data['status-code'] == 200",
        ],
    )
    assert result.exit_code == 0, result.stderr

    data = result.stdout
    payload = json.loads(data)
    assert payload["status"] == "fail"


@pytest.mark.filterwarnings("ignore:Unverified HTTPS request is being made to host")
def test_run_simple_config(simple_config_filename):
    result = runner.invoke(app, ["run", "--config", simple_config_filename])
    assert result.exit_code == 0
    data = result.stdout
    json.loads(data)


def test_run_invalid_config_unknown_check(invalid_config_filename):
    result = runner.invoke(app, ["run", "--config", invalid_config_filename])
    assert result.exit_code != 0


def test_run_valid_config_expected_fail_check(valid_config_expected_fail_filename):
    result = runner.invoke(
        app, ["run", "--config", valid_config_expected_fail_filename]
    )
    assert result.exit_code == 0
    data = result.stdout
    json.loads(data)


def test_run_valid_config_unexpected_failures(valid_config_unexpected_fail_filename):
    result = runner.invoke(
        app, ["run", "--config", valid_config_unexpected_fail_filename]
    )
    assert result.exit_code == 0
    data = result.stdout
    json.loads(data)


def test_run_valid_dns_config(dns_config_filename):
    result = runner.invoke(app, ["run", "--config", dns_config_filename])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    for assertion in data["assertions"]:
        for result in assertion["results"]:
            assert "status" in result
            assert result["status"] == "pass"


def test_run_valid_dns_custom_config(dns_config_with_validation_filename):
    result = runner.invoke(
        app, ["run", "--config", dns_config_with_validation_filename]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)

    for assertion in data["assertions"]:
        for result in assertion["results"]:
            assert "status" in result
            assert result["status"] == "pass"


def test_run_http_config_with_headers(http_headers_config_filename):
    result = runner.invoke(app, ["run", "--config", http_headers_config_filename])
    assert result.exit_code == 0, result.stderr
    data = result.stdout
    response = json.loads(data)

    test_result = response["assertions"][0]["results"][0]
    assert test_result["spec"]["headers"]["X-Test-Header"] == "value"
    assert "X-Test-Header" in json.loads(test_result["data"]["body"])["headers"]
