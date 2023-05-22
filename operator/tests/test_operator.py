import time
import subprocess
from kopf.testing import KopfRunner


def test_operator(k8s_namespace, test_file_path):
    # Ensure CRDs are already installed

    with KopfRunner(["run", "-A", "netchecks_operator/main.py"]) as runner:
        # Remove all existing network assertions
        subprocess.run(
            f"kubectl delete -A NetworkAssertions --all --timeout=30s",
            shell=True,
        )
        time.sleep(3.0)  # give it some time to react

        subprocess.run(
            f"kubectl apply -f {test_file_path('http-job.yaml')} -n {k8s_namespace}",
            shell=True,
            check=True,
        )
        time.sleep(5.0)  # allow operator to react (pull images, retry once)


    assert runner.exit_code == 0
    assert runner.exception is None
    list_assertions_response = subprocess.run(
        f"kubectl get networkassertions -n {k8s_namespace}", shell=True, check=True, capture_output=True
    )
    jobs_response = subprocess.run(
        f"kubectl get jobs -n {k8s_namespace}", shell=True, check=True, capture_output=True
    )
    assert b'http-should-work' in list_assertions_response.stdout
    assert b'http-should-work' in jobs_response.stdout

    assert "Pod monitoring complete" in runner.stdout
    assert "http-should-work" in runner.stdout

    time.sleep(3)
    # Now delete the networkassertion and ensure the other resources get deleted
    with KopfRunner(["run", "-A", "netchecks_operator/main.py"]) as runner:
        subprocess.run(
            f"kubectl delete -f {test_file_path('http-job.yaml')} -n {k8s_namespace} --timeout=30s",
            shell=True,
            check=True,
        )

        time.sleep(5.0)  # give it some time to react

        # Help it out incase something went wrong (we are testing after all)
        subprocess.run(
            f"kubectl delete -A Jobs -l app.kubernetes.io/component=probe -l app.kubernetes.io/name=netchecks --timeout=30s",
            shell=True,
        )

    assert (
        f"networkassertion delete handler called name=http-should-work namespace={k8s_namespace}"
        in runner.stdout
    )
