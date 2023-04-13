import os
import subprocess
import random
import string
from typing import Optional

from pytest import fixture

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'testdata',
    )


def random_lower_string(length: Optional[int] = 32) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


@fixture()
def test_file_path():
    def get_test_file(filename):
        return os.path.join(TEST_DATA_DIR, filename)
    return get_test_file


@fixture(scope="session")
def k8s_namespace():
    name = f"netchecks-test-{random_lower_string(length=6)}"
    subprocess.run(f"kubectl create namespace {name}",
                       shell=True, check=True)
    yield name
    print("Deleting namespace")
    subprocess.run(f"kubectl delete namespace {name}", shell=True, check=True)
