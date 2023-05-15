from importlib import metadata

try:
    NETCHECK_VERSION = metadata.version("netcheck")
except metadata.PackageNotFoundError:
    NETCHECK_VERSION = "unknown"

OUTPUT_JSON_VERSION = "dev"  # set to v1 once stable
