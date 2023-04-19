# Netchecks

<p align="center">
  <img alt="Netchecks Logo" src=".github/logo.png" width="150" />
</p>

<div align="center">

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/netcheck)
[![Coverage Status](https://coveralls.io/repos/github/hardbyte/netcheck/badge.svg?branch=main)](https://coveralls.io/github/hardbyte/netcheck?branch=main)
![PyPI - Downloads](https://img.shields.io/pypi/dm/netcheck)

</div>

**Netchecks** is a set of tools for testing network conditions and asserting that they are as expected.

There are two main components:
- **Netchecks Operator** - Kubernetes Operator that runs network checks and reports results as `PolicyReport` resources. See the [operator README](operator/README.md) for more details and the full documentation can be found at [https://docs.netchecks.io](https://docs.netchecks.io)
- **Netcheck CLI and Python Library** - Command line tool for running network checks and asserting that they are as expected. Keep reading for the quickstart.


# Netcheck Command Line Tool Quickstart

`netcheck` is a configurable command line application that can be used to test network conditions are as expected.

## Installation

Install the Python package:

```
pip install netcheck
```

Or run with Docker:

```shell
docker run -it ghcr.io/hardbyte/netchecks:main
```

### Individual Assertions

By default `netcheck` outputs a JSON result to stdout including response details: 

```shell
$ netcheck dns
```

```json
{
  "spec": {
    "type": "dns",
    "nameserver": null,
    "host": "github.com",
    "timeout": 30.0
  },
  "data": {
    "canonical_name": "github.com.",
    "expiration": 1675825244.2986872,
    "response": "id 6176\nopcode QUERY\nrcode NOERROR\nflags QR RD RA\nedns 0\npayload 65494\n;QUESTION\ngithub.com. IN A\n;ANSWER\ngithub.com. 60 IN A 20.248.137.48\n;AUTHORITY\n;ADDITIONAL",
    "A": [
      "20.248.137.48"
    ],
    "startTimestamp": "2023-02-08T02:59:44.248174",
    "endTimestamp": "2023-02-08T02:59:44.298773"
  },
  "status": "pass"
}

```

Pass the `-v` flag to see log messages.

Each check can be configured, e.g. you can specify the `server` and `host` for a `dns` check, and
tell `netcheck` whether a particular configuration is expected to pass or fail:


```shell
netcheck dns --server 1.1.1.1 --host hardbyte.nz --should-pass
```

```json
{
  "spec": {
    "type": "dns",
    "nameserver": "1.1.1.1",
    "host": "hardbyte.nz",
    "timeout": 30.0
  },
  "data": {
    "canonical_name": "hardbyte.nz.",
    "expiration": 1675827006.4370346,
    "response": "id 23453\nopcode QUERY\nrcode NOERROR\nflags QR RD RA\nedns 0\npayload 1232\noption EDE 10: for DNSKEY nz., id = 13646\n;QUESTION\nhardbyte.nz. IN A\n;ANSWER\nhardbyte.nz. 985 IN A 209.58.165.79\n;AUTHORITY\n;ADDITIONAL",
    "A": [
      "209.58.165.79"
    ],
    "response-code": "NOERROR",
    "startTimestamp": "2023-02-08T03:13:41.402313",
    "endTimestamp": "2023-02-08T03:13:41.437115"
  },
  "status": "pass"
}
```

Netcheck can handle checks that are expected to fail:
```shell
$ netcheck dns --server=1.1.1.1 --host=made.updomain --should-fail
```

Note the resulting status will show **pass** if the check fails as expected, and **fail** if the check passes unexpectedly!

netcheck has built in default validation for each check type. For example, the `dns` check will pass if the DNS response code is `NOERROR`, there is at least one `A` record, and resolver responds in under 10 seconds. Custom validation is also possible, see the [Custom Validation](#custom-validation) section below.


## Custom Validation

Custom validation can be added to checks by providing a `validation-rule` option on the command line, or a `validation` key in the rules of a test spec when configuring via json. 

For example to override the default validation for the `dns` check to check that the A record resolves to a particular IP:

```shell
netcheck dns --host github.com --validation-rule "data['A'].contains('20.248.137.48')"
```

The validation rule is a CEL expression that is evaluated with the `data` returned by the check and `spec` objects in scope. For an introduction to CEL see https://github.com/google/cel-spec/blob/master/doc/intro.md



## http checks

`http` checks are also available:

Assert that GitHub's status page includes the text "GitHub lives!" and that the response code is 200:

```shell
netcheck http --url=https://github.com/status --validation-rule "data.body.contains('GitHub lives!') && data['status-code'] in [200, 201]"
```

Provide a header with a request:

```shell
netcheck http --url https://pie.dev/headers --header "X-Header:special"
```

Validate that the response body is valid JSON and includes a `headers` object containing the `X-Header` key with the value `special`:

```shell
netcheck http --url https://pie.dev/headers \
  --header "X-Header:special" \
  --validation-rule "parse_json(data.body).headers['X-Header'] == 'special'"
```


Ensure that a POST request fails:

```shell
$ netcheck http --method=post --url=https://s3.ap-southeast-2.amazonaws.com --should-fail
```


## Configuration via file

The main way to run `netcheck` is passing in a list of assertions. 
A json file can be provided with a list of assertions to be checked:

```json
{
  "assertions": [
    {
      "name":  "deny-cloudflare-dns", 
      "rules": [
        {"type": "dns", "server":  "1.1.1.1", "host": "github.com"}
      ]
    }
  ]
}
```

And the `run` command can be called:


```shell
$ netcheck run --config tests/testdata/dns-config.json
```

```json
{
  "type": "netcheck-output",
  "outputVersion": "dev",
  "metadata": {
    "creationTimestamp": "2022-12-27T22:16:43.438696",
    "version": "0.1.7"
  },
  "assertions": [
    {
      "name": "default-dns",
      "results": [
        {
          "status": "pass",
          "spec": {
            "type": "dns",
            "shouldFail": false,
            "nameserver": null,
            "host": "github.com",
            "timeout": null
          },
          "data": {
            "startTimestamp": "2022-12-27T22:16:43.438704",
            "A": [
              "20.248.137.48"
            ],
            "endTimestamp": "2022-12-27T22:16:43.455657"
          }
        }
      ]
    }
  ]
}
```

Multiple assertions with multiple rules can be specified in the config file, configuration can be provided
to each rule such as headers and custom validation:

```json
{
  "assertions": [
    {"name":  "get-with-header", "rules": [
      {"type": "http", "url": "https://pie.dev/headers", "headers": {"X-Test-Header":  "value"}},
      {"type": "http", "url": "https://pie.dev/headers", "headers": {"X-Header": "secret"}, "validation": "parse_json(data.body).headers['X-Header'] == 'secret'" }
    ]}
  ]
}
```

## Development

Update version in pyproject.toml, push to `main` and create a release on GitHub. Pypi release will be carried
out by GitHub actions. 

Install dev dependencies with Poetry:

```shell
poetry install --with dev
```

### Manual Release 
To release manually, use Poetry:

```shell
poetry version patch
poetry build
poetry publish
```

### Testing

Pytest is used for testing. 

```shell
poetry run pytest
```
