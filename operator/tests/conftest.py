import os
import subprocess
import random
import string
from typing import Optional

from pytest import fixture

NETCHECKS_CHART_DIR = os.path.realpath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        os.path.pardir,
        'charts',
        'netchecks'
    )
)

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
def netchecks_crds():
    crds_folder_path = os.path.join(NETCHECKS_CHART_DIR, 'crds')
    print(crds_folder_path)
    subprocess.run(f"kubectl apply -f {crds_folder_path}", shell=True, check=True)
    yield None
    print("Deleting CRDs")
    try:
        subprocess.run(f"kubectl delete -f {crds_folder_path}", shell=True, check=True)
    except subprocess.CalledProcessError:
        pass



@fixture(scope="session")
def netchecks(k8s_namespace):
    try:
        subprocess.run(f'helm upgrade --install netchecks-operator {NETCHECKS_CHART_DIR} -n {k8s_namespace} --set operator.image.tag=latest', shell=True, check=True)
        subprocess.run(f"kubectl wait Deployment -n {k8s_namespace} -l app.kubernetes.io/instance=netchecks-operator --for condition=Available --timeout=30s", shell=True, check=True)

        yield None

    finally:
        print("Uninstalling netchecks-operator")
        try:
            subprocess.run(f"kubectl delete -A NetworkAssertions --all", shell=True, check=True)
            subprocess.run(f"helm uninstall netchecks-operator -n {k8s_namespace}", shell=True, check=True)
        except subprocess.CalledProcessError:
            pass


@fixture(scope="session")
def k8s_namespace():
    name = f"netchecks-test-{random_lower_string(length=6)}"
    subprocess.run(f"kubectl create namespace {name}",
                       shell=True, check=True)
    yield name
    print("Deleting namespace")
    subprocess.run(f"kubectl delete namespace {name}", shell=True, check=True)
