import os

from pytest import fixture

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "testdata",
)


@fixture()
def simple_config_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config.json")


@fixture()
def dns_config_filename():
    return os.path.join(TEST_DATA_DIR, "dns-config.json")


@fixture()
def dns_config_with_validation_filename():
    return os.path.join(TEST_DATA_DIR, "dns-config-custom-validation.json")

@fixture()
def config_with_context_filename():
    return os.path.join(TEST_DATA_DIR, "config-with-context.json")


@fixture()
def data_filename():
    return os.path.join(TEST_DATA_DIR, "data.json")


@fixture()
def data_dir_path():
    return os.path.join(TEST_DATA_DIR, "dir-of-data")


@fixture()
def invalid_config_filename():
    return os.path.join(TEST_DATA_DIR, "invalid-config-unknown-check.json")


@fixture()
def valid_config_expected_fail_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config-with-expected-failures.json")


@fixture()
def valid_config_unexpected_fail_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config-with-unexpected-failures.json")


@fixture()
def http_headers_config_filename():
    return os.path.join(TEST_DATA_DIR, "http-with-headers.json")
