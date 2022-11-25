import os

from pytest import fixture

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'testdata',
    )


@fixture()
def simple_config_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config.json")


@fixture()
def invalid_config_filename():
    return os.path.join(TEST_DATA_DIR, "invalid-config-unknown-check.json")


@fixture()
def valid_config_expected_fail_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config-with-expected-failures.json")



@fixture()
def valid_config_unexpected_fail_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config-with-unexpected-failures.json")


