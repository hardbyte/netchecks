![](.github/logo.png)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/netcheck) [![Coverage Status](https://coveralls.io/repos/github/hardbyte/netcheck/badge.svg?branch=main)](https://coveralls.io/github/hardbyte/netcheck?branch=main) ![PyPI - Downloads](https://img.shields.io/pypi/dm/netcheck)

# Netchecks Command Line Tool

Configurable command line application that can be used to test network conditions are as expected.


## Quickstart



### Installation

Install the Python package:

```
pip install netcheck
```

Or run with Docker:

```shell
docker run -it ghcr.io/netchecks/netchecks:latest
```

### Individual Assertions

By default `netcheck` outputs a JSON result to stdout: 

```shell
netcheck dns
{
  "status": "pass",
  "spec": {
    "type": "dns",
    "nameserver": null,
    "host": "github.com",
    "timeout": 30.0
  },
  "data": {
    "startTimestamp": "2022-12-27T22:07:44.592562",
    "A": [
      "20.248.137.48"
    ],
    "endTimestamp": "2022-12-27T22:07:44.610156"
  }
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
  "status": "pass",
  "spec": {
    "type": "dns",
    "nameserver": "1.1.1.1",
    "host": "hardbyte.nz",
    "timeout": 30.0
  },
  "data": {
    "startTimestamp": "2022-12-27T22:09:33.449567",
    "A": [
      "209.58.165.79"
    ],
    "endTimestamp": "2022-12-27T22:09:33.467162"
  }
}
```

Netcheck can check that particular checks fail:
```shell
$ netcheck dns --server=1.1.1.1 --host=made.updomain --should-fail
```

Note the resulting status will show **pass** if the check fails as expected, and **fail** if the check passes unexpectedly!

```json
{
  "status": "pass",
  "spec": {
    "type": "dns",
    "nameserver": "1.1.1.1",
    "host": "made.updomain",
    "timeout": 30.0
  },
  "data": {
    "startTimestamp": "2022-12-27T22:10:07.726285",
    "exception-type": "NXDOMAIN",
    "exception": "The DNS query name does not exist: made.updomain.",
    "endTimestamp": "2022-12-27T22:10:07.743219"
  }
}
```

A few http checks are also available:

```shell
netcheck http --method=get --url=https://s3.ap-southeast-2.amazonaws.com --should-pass
```

```shell
$ netcheck http --method=post --url=https://s3.ap-southeast-2.amazonaws.com --should-fail
```

```json
{
  "status": "pass",
  "spec": {
    "type": "http",
    "timeout": 30.0,
    "verify-tls-cert": true,
    "method": "post",
    "url": "https://s3.ap-southeast-2.amazonaws.com"
  },
  "data": {
    "startTimestamp": "2022-12-27T22:11:33.696001",
    "status-code": 405,
    "exception-type": "HTTPError",
    "exception": "405 Client Error: Method Not Allowed for url: https://s3.ap-southeast-2.amazonaws.com/",
    "endTimestamp": "2022-12-27T22:11:33.900833"
  }
}
```

### Configuration via file

The main way to run `netcheck` is passing in a list of assertions. 
A json file can be provided with a list of assertions to be checked:

```json
{
  "assertions": [
    {
      "name":  "deny-cloudflare-dns", 
      "rules": [
        {"type": "dns", "server":  "1.1.1.1", "host": "github.com", "expected": "pass"}
      ]
    }
  ]
}
```

And the command can be called:


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

## Coming Soon

- Propagation of optional rule names and messages through to the output
- Expected status codes and specific DNS errors.
- JSON Schema for config file and outputs
- More checks

## Development

Update version in pyproject.toml, push to `main` and create a release on GitHub. Pypi release will be carried
out by GitHub actions. 


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
