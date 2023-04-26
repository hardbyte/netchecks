import pkg_resources


try:
    NETCHECK_VERSION = pkg_resources.get_distribution("netcheck").version
except pkg_resources.DistributionNotFound:
    NETCHECK_VERSION = "unknown"

OUTPUT_JSON_VERSION = "dev"  # set to v1 once stable
