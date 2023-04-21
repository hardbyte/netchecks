import json
import os
import time
import subprocess

import pytest
from kubernetes import client

INCLUDE_CILIUM_TESTS = os.getenv('INCLUDE_CILIUM_TESTS')


@pytest.mark.skipif(INCLUDE_CILIUM_TESTS is None, reason="Cilium is not installed")
def test_k8s_version_with_installed_operator(netchecks, k8s_namespace, example_dir_path):
    dns_restrictions_dir = example_dir_path('cilium-dns-restrictions')

    # Apply the example DNS restrictions and network assertions
    subprocess.run(f"kubectl apply -n {k8s_namespace} -f {dns_restrictions_dir}", shell=True, check=True)

    # Assert that a CronJob gets created in the same namespace
    for i in range(10):
        jobs_response = subprocess.run(f"kubectl get cronjobs -n {k8s_namespace}", shell=True, check=True, capture_output=True)
        if b'dns-restrictions-should-work' in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Now wait for the job to get created (up to 1 minute)
    for i in range(10):
        jobs_response = subprocess.run(f"kubectl get jobs -n {k8s_namespace} -l app.kubernetes.io/instance=dns-restrictions-should-work", shell=True, check=True, capture_output=True)
        if b'dns-restrictions-should-work' in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Now the job exists, wait for the job to complete
    subprocess.run(f"kubectl wait Job -l app.kubernetes.io/instance=dns-restrictions-should-work -n {k8s_namespace} --for condition=complete --timeout=120s", shell=True, check=True)

    # Assert that a PolicyReport gets created in the same namespace
    for i in range(20):
        policy_report_response = subprocess.run(f"kubectl get policyreports -n {k8s_namespace}", shell=True, check=True, capture_output=True)
        if b'dns-restrictions-should-work' in policy_report_response.stdout:
            break
        time.sleep(1.3**i)
    assert b'dns-restrictions-should-work' in policy_report_response.stdout

    # Now get the detailed policy report results
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(f"""kubectl get policyreport/dns-restrictions-should-work -n {k8s_namespace} -o {results_filter}""", shell=True, check=True, capture_output=True)
    policy_report_results = json.loads(policy_report_results_response.stdout)
    assert len(policy_report_results) > 1
    for result in policy_report_results:
        assert result['category'] == 'dns'
        assert result['result'] == 'pass', str(result)
        assert result['source'] == 'netchecks'

        test_spec = json.loads(result['properties']['spec'])
        test_data = json.loads(result['properties']['data'])

    # Delete the network assertion
    subprocess.run(f"kubectl delete -n {k8s_namespace} -f {dns_restrictions_dir}", shell=True, check=True)
