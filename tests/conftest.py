import os

from pytest import fixture

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'testdata',
    )


@fixture()
def simple_config_filename():
    return os.path.join(TEST_DATA_DIR, "simple-config.json")