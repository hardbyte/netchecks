
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/netcheck) [![Coverage Status](https://coveralls.io/repos/github/hardbyte/netcheck/badge.svg?branch=main)](https://coveralls.io/github/hardbyte/netcheck?branch=main) ![PyPI - Downloads](https://img.shields.io/pypi/dm/netcheck)

# Network Health Check

Configurable command line application that can be used to test network conditions are as expected.

Very early work in progress version!

## Quickstart



### Installation

Install the Python package:

```
pip install netcheck
```

Or use with Docker:

```shell
docker pull ghcr.io/hardbyte/netcheck:latest
```

### Individual Assertions

By default `netcheck` outputs a JSON result to stdout: 

```shell
netcheck dns
{
  "type": "dns",
  "nameserver": null,
  "host": "github.com",
  "timeout": 30.0,
  "result": "pass",
  "data": {
    "A": [
      "20.248.137.48"
    ]
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
  "type": "dns",
  "nameserver": "1.1.1.1",
  "host": "hardbyte.nz",
  "timeout": 30.0,
  "result": "pass",
  "data": {
    "A": [
      "209.58.165.79"
    ]
  }
}
```

Netcheck can check that particular checks fail:
```shell
$ netcheck dns --server=1.1.1.1 --host=made.updomain --should-fail
```
```json
{
  "type": "dns",
  "nameserver": "1.1.1.1",
  "host": "made.updomain",
  "timeout": 30.0,
  "result": "pass",
  "data": {
    "exception-type": "NXDOMAIN",
    "exception": "The DNS query name does not exist: made.updomain."
  }
}
```

```shell
netcheck http --method=get --url=https://s3.ap-southeast-2.amazonaws.com --should-pass
```

```shell
$ netcheck http --method=post --url=https://s3.ap-southeast-2.amazonaws.com --should-fail
```

```json
{
  "type": "http",
  "timeout": 30.0,
  "verify-tls-cert": true,
  "method": "post",
  "url": "https://s3.ap-southeast-2.amazonaws.com",
  "result": "pass",
  "data": {
    "status-code": 405,
    "exception-type": "HTTPError",
    "exception": "405 Client Error: Method Not Allowed for url: https://s3.ap-southeast-2.amazonaws.com/"
  }
}
```

### Configuration via file

The main way to run `netcheck` is passing in a list of assertions. 
A json file can be provided with a list of assertions to be checked:

```json
{
  "assertions": [
    {"name":  "deny-cloudflare-dns", "rules": [{"type": "dns", "server":  "1.1.1.1", "host": "github.com", "expected": "pass"}] }
  ]
}
```

And the command can be called:
```shell
netcheck run --config example-config.json 
```

Or with `--verbose`:

```shell
$ netcheck run --config tests/testdata/simple-config.json
```

```json
[
  {
    "type": "dns",
    "nameserver": null,
    "host": "github.com",
    "timeout": null,
    "result": "pass",
    "data": {
      "A": [
        "20.248.137.48"
      ]
    }
  },
  {
    "type": "dns",
    "nameserver": "1.1.1.1",
    "host": "github.com",
    "timeout": null,
    "result": "pass",
    "data": {
      "A": [
        "20.248.137.48"
      ]
    }
  },
  {
    "type": "http",
    "timeout": null,
    "verify-tls-cert": true,
    "method": "get",
    "url": "https://github.com/status",
    "result": "pass",
    "data": {
      "status-code": 200
    }
  },
  {
    "type": "http",
    "timeout": null,
    "verify-tls-cert": false,
    "method": "get",
    "url": "https://self-signed.badssl.com/",
    "result": "pass",
    "data": {
      "status-code": 200
    }
  },
  {
    "type": "http",
    "timeout": null,
    "verify-tls-cert": true,
    "method": "get",
    "url": "https://self-signed.badssl.com/",
    "result": "pass",
    "data": {
      "exception-type": "SSLError",
      "exception": "HTTPSConnectionPool(host='self-signed.badssl.com', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:997)')))"
    }
  }
]
```
## Development

Update version and create a release on GitHub, Pypi release will be carried out by a Github action. 

To release manually, use Poetry:

```
poetry version patch
poetry build
poetry publish
```
