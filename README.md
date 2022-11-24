# Network Health Check

Configurable command line application that can be used to test network conditions are as expected.

Very early work in progress version!

## Quickstart



### Installation

```
pip install netcheck
```


### Individual Assertions

By default `netcheck` won't output anything if the check passes. 

```
$ poetry run netcheck dns
```

Pass the `-v` flag to see what is going on:

```
$ poetry run netcheck dns -v
DNS check with nameserver None looking up host 'github.com'
✔ Passed (as expected)
{
  "type": "dns",
  "nameserver": null,
  "host": "github.com",
  "timeout": 10,
  "result": {
    "A": [
      "20.248.137.48"
    ]
  }
}
```

Each check can be configured, e.g. you can specify the `server` and `host` for a `dns` check, and
tell `netcheck` whether a particular configuration is expected to pass or fail:

```
$ poetry run netcheck dns --server 1.1.1.1 --host hardbyte.nz --should-pass -v
DNS check with nameserver 1.1.1.1 looking up host 'hardbyte.nz'
✔ Passed (as expected)
{
  "type": "dns",
  "nameserver": "1.1.1.1",
  "host": "hardbyte.nz",
  "timeout": 10,
  "result": {
    "A": [
      "209.58.165.79"
    ]
  }
}

```

A few other individual examples:
```
$ netcheck dns --server=1.1.1.1 --host=made.updomain --should-fail -v
DNS check with nameserver 1.1.1.1 looking up host 'made.updomain'
❌ Failed. As expected.
{
  "type": "dns",
  "nameserver": "1.1.1.1",
  "host": "made.updomain",
  "timeout": 10,
  "result": {
    "exception-type": "NXDOMAIN",
    "exception": "The DNS query name does not exist: made.updomain."
  }
}

$ netcheck http --method=get --url=https://s3.ap-southeast-2.amazonaws.com --should-pass
$ poetry run netcheck http --method=post --url=https://s3.ap-southeast-2.amazonaws.com --should-fail -v
http check with url 'https://s3.ap-southeast-2.amazonaws.com'
❌ Failed. As expected.
{
  "type": "http",
  "method": "post",
  "url": "https://s3.ap-southeast-2.amazonaws.com",
  "result": {
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
```
$ poetry run netcheck run --config config.json 
Loaded 2 assertions
Running test 'cloudflare-dns'
Running test 'github-status'
```

Or with `--verbose`:

```shell
$ poetry run netcheck run --config tests/testdata/simple-config.json -v
Loaded 2 assertions
Running test 'cloudflare-dns'
DNS check with nameserver 1.1.1.1 looking up host 'github.com'
✔ Passed (as expected)
{
  "type": "dns",
  "nameserver": "1.1.1.1",
  "host": "github.com",
  "timeout": 10,
  "result": {
    "A": [
      "20.248.137.48"
    ]
  }
}
Running test 'github-status'
http check with url 'https://github.com/status'
✔ Passed (as expected)
{
  "type": "http",
  "method": "get",
  "url": "https://github.com/status",
  "result": {
    "status-code": 200
  }
}

```

## Development

Build and publish with poetry. First update the version.

```
poetry version patch
poetry build
poetry publish
```
