import json

from typer.testing import CliRunner

from netcheck.cli import app

runner = CliRunner(mix_stderr=False)


# To write the stderr and stdout to separate files use:
# poetry run netcheck http -v 2> errlog > stdout

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


def test_default_http_check():
    result = runner.invoke(app, ["http"])
    assert result.exit_code == 0
    assert len(result.stderr) == 0
    data = result.stdout
    json.loads(data)


def test_verbose_default_http_check():
    result = runner.invoke(app, ["http", "-v"])
    assert result.exit_code == 0
    assert "http" in result.stderr
    assert "Passed" in result.stderr
    assert "github.com/status" in result.stderr
    data = result.stdout
    json.loads(data)


def test_run_simple_config(simple_config_filename):
    result = runner.invoke(app, ["run", "--config", simple_config_filename])
    assert result.exit_code == 0
    data = result.stdout
    json.loads(data)

