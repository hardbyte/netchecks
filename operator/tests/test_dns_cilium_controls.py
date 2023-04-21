import json
import os
import time
import subprocess

import pytest
from kubernetes import client

INCLUDE_CILIUM_TESTS = os.getenv('INCLUDE_CILIUM_TESTS')


@pytest.mark.skipif(INCLUDE_CILIUM_TESTS is None, reason="Cilium is not installed")
def test_k8s_version_with_installed_operator(netchecks, k8s_namespace, test_file_path):
    http_assertion_manifest = test_file_path('http-job.yaml')

    subprocess.run(f"kubectl apply -n {k8s_namespace} -f {http_assertion_manifest}", shell=True, check=True)

    # Assert that a Job gets created in the same namespace
    for i in range(10):
        jobs_response = subprocess.run(f"kubectl get jobs -n {k8s_namespace}", shell=True, check=True, capture_output=True)
        if b'http-should-work' in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Wait for the job to complete
    subprocess.run(f"kubectl wait Job/http-should-work -n {k8s_namespace} --for condition=complete --timeout=120s", shell=True, check=True)

    # Assert that a PolicyReport gets created in the same namespace
    for i in range(10):
        policy_report_response = subprocess.run(f"kubectl get policyreports -n {k8s_namespace}", shell=True, check=True, capture_output=True)
        if b'http-should-work' in policy_report_response.stdout:
            break
        time.sleep(1.5**i)
    assert b'http-should-work' in policy_report_response.stdout

    summary_filter = "jsonpath='{.summary}'"
    policy_report_summary = subprocess.run(f"""kubectl get policyreport/http-should-work -n {k8s_namespace} -o {summary_filter}""", shell=True, check=True, capture_output=True)
    policy_report_summary = json.loads(policy_report_summary.stdout)

    assert policy_report_summary['pass'] >= 1
    assert 'fail' not in policy_report_summary

    # Now get the detailed policy report results
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(f"""kubectl get policyreport/http-should-work -n {k8s_namespace} -o {results_filter}""", shell=True, check=True, capture_output=True)
    policy_report_results = json.loads(policy_report_results_response.stdout)

    """
    results:
      - category: http
        message: Rule from kubernetes-version
        policy: kubernetes-version
        properties:
          data: >-
    """
    for result in policy_report_results:
        assert result['category'] == 'http'
        assert result['policy'] == 'kubernetes-version'
        assert result['result'] == 'pass'
        assert result['source'] == 'netchecks'

        test_spec = json.loads(result['properties']['spec'])
        assert test_spec['type'] == 'http'
        assert test_spec['method'] == 'get'
        assert test_spec['verify-tls-cert'] == False
        assert test_spec['url'] == 'https://kubernetes.default.svc/version'

        test_data = json.loads(result['properties']['data'])
        assert test_data['status-code'] == 200

    # Delete the network assertion
    subprocess.run(f"kubectl delete -n {k8s_namespace} -f {http_assertion_manifest}", shell=True, check=True)
