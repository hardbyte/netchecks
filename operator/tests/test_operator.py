import time
import subprocess
from kopf.testing import KopfRunner


def test_operator(netchecks_crds, k8s_namespace, test_file_path):
    with KopfRunner(["run", "-A", "netchecks_operator/main.py"]) as runner:
        # Remove all existing network assertions
        subprocess.run(
            f"kubectl delete -A NetworkAssertions --all",
            shell=True,
        )
        time.sleep(5.0)  # give it some time to react

        subprocess.run(
            f"kubectl apply -f {test_file_path('http-job.yaml')} -n {k8s_namespace}",
            shell=True,
            check=True,
        )
        time.sleep(5)  # allow operator to react (pull images, retry once)

        list_assertions_response = subprocess.run(
            f"kubectl get networkassertions -n {k8s_namespace}", shell=True, check=True
        )
        jobs_response = subprocess.run(
            f"kubectl get jobs -n {k8s_namespace}", shell=True, check=True
        )

        subprocess.run(
            f"kubectl delete -f {test_file_path('http-job.yaml')} -n {k8s_namespace}",
            shell=True,
            check=True,
        )
        time.sleep(3.0)  # give it some time to react

    assert runner.exit_code == 0
    assert runner.exception is None

    # assert b'http-should-work' in list_assertions_response.stdout
    # assert b'http-should-work' in jobs_response.stdout

    assert "Pod monitoring complete" in runner.stdout
    assert "http-should-work" in runner.stdout

    # The PolicyReport either already exists (from other tests), or gets created.

    assert (
        f"networkassertion delete handler called name=http-should-work namespace={k8s_namespace}"
        in runner.stdout
    )
