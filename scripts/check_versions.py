#!/usr/bin/env python3

import sys
import tomllib
from pathlib import Path

import yaml


def read_toml(file: str) -> dict:
    with open(file, "rb") as f:
        return tomllib.load(f)


def read_yaml(file: str) -> dict:
    with open(file, "r") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    # Optional: `--expect v0.11.0` (or `0.11.0`) additionally requires every version
    # to equal the given one. Used by the release workflow to check the git tag.
    expected = None
    if len(sys.argv) == 3 and sys.argv[1] == "--expect":
        expected = sys.argv[2].removeprefix("v")
    elif len(sys.argv) != 1:
        print(f"usage: {sys.argv[0]} [--expect vX.Y.Z]", file=sys.stderr)
        sys.exit(2)

    git_root_path = Path(__file__).resolve().parent.parent
    cli_toml_path = git_root_path / "pyproject.toml"
    operator_toml_path = git_root_path / "operator" / "Cargo.toml"
    operator_chart_path = git_root_path / "operator" / "charts" / "netchecks" / "Chart.yaml"

    cli_toml = read_toml(cli_toml_path)
    operator_toml = read_toml(operator_toml_path)
    operator_chart_yaml = read_yaml(operator_chart_path)

    cli_version = cli_toml["project"]["version"]
    operator_version = operator_toml["package"]["version"]
    operator_chart_version = operator_chart_yaml["appVersion"]

    if len({cli_version, operator_version, operator_chart_version}) == 1:
        if expected is not None and cli_version != expected:
            print(
                f"Error: versions are {cli_version} but the tag says {expected}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Versions match! ({cli_version})")
        sys.exit(0)
    else:
        print(
            f"Error: Versions do not match\n{cli_toml_path}: {cli_version}\n{operator_toml_path}: {operator_version}\n{operator_chart_path}: {operator_chart_version}",
            file=sys.stderr,
        )
        sys.exit(1)
