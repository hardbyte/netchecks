import time
import subprocess
from kopf.testing import KopfRunner


def test_operator(k8s_namespace, test_file_path):

    with KopfRunner(['run', '-A', '--verbose', 'main.py']) as runner:
        # do something while the operator is running.

        subprocess.run(f"kubectl apply -f {test_file_path('http-job.yaml')} -n {k8s_namespace}",
                       shell=True, check=True)
        time.sleep(10)  # give it some time to react and to sleep and to retry

        list_assertions_response = subprocess.run(f"kubectl get networkassertions -n {k8s_namespace}", shell=True, check=True)
        jobs_response = subprocess.run(f"kubectl get jobs -n {k8s_namespace}", shell=True, check=True)

        subprocess.run(f"kubectl delete -f {test_file_path('http-job.yaml')} -n {k8s_namespace}", shell=True, check=True)
        time.sleep(1)  # give it some time to react

    assert runner.exit_code == 0
    assert runner.exception is None

    #assert b'http-should-work' in list_assertions_response.stdout
    #assert b'http-should-work' in jobs_response.stdout

    assert 'Pod monitoring complete' in runner.stdout
    assert 'http-should-work' in runner.stdout
    assert 'PolicyReport created' in runner.stdout
    assert f'networkassertion delete handler called name=http-should-work namespace={k8s_namespace}' in runner.stdout
