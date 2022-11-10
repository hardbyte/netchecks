# Network Health Check

Configurable command line application that can be used to test network conditions are as expected.

Very early work in progress version!

## Quickstart


### Installation

```
pip install netcheck
```


### Individual Assertions


```
$ poetry run netcheck check --type=dns --should-fail
Passed but was expected to fail.
{'type': 'dns', 'nameserver': None, 'host': 'github.com', 'A': ['20.248.137.48']}
```

A few other individual examples:
```
./netcheck check --type=dns --server=1.1.1.1 --host=hardbyte.nz --should-fail
./netcheck check --type=dns --server=1.1.1.1 --host=hardbyte.nz --should-pass
./netcheck check --type=http --method=get --url=https://s3.ap-southeast-2.amazonaws.com --should-pass
```

Output is quiet by default, json available with `--json` (TODO).


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
```


## Development

Build and publish with poetry. First update the version.

```
poetry version patch
poetry build
poetry publish
```
