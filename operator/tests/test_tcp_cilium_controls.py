import json
import os
import time
import subprocess

import pytest


INCLUDE_CILIUM_TESTS = os.getenv("INCLUDE_CILIUM_TESTS")


@pytest.mark.skipif(INCLUDE_CILIUM_TESTS is None, reason="Cilium is not installed")
def test_tcp_egress_with_cilium_policy(netchecks, k8s_namespace, example_dir_path):
    tcp_restrictions_dir = example_dir_path("cilium-tcp-egress-restrictions")

    # Apply the Cilium network policy first and let it propagate
    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {tcp_restrictions_dir}/tcp-egress-netpol.yaml",
        shell=True,
        check=True,
    )
    time.sleep(5)

    # Apply the NetworkAssertion
    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {tcp_restrictions_dir}/tcp-egress-assertion.yaml",
        shell=True,
        check=True,
    )

    # Wait for the CronJob to be created
    for i in range(10):
        cronjobs_response = subprocess.run(
            f"kubectl get cronjobs -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if b"tcp-egress-restrictions-should-work" in cronjobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Wait for a Job to be created from the CronJob
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl get jobs -n {k8s_namespace} -l app.kubernetes.io/instance=tcp-egress-restrictions-should-work",
            shell=True,
            check=True,
            capture_output=True,
        )
        if b"tcp-egress-restrictions-should-work" in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Wait for the job to complete
    subprocess.run(
        f"kubectl wait Job -l app.kubernetes.io/instance=tcp-egress-restrictions-should-work -n {k8s_namespace} --for condition=complete --timeout=120s",
        shell=True,
        check=True,
    )

    # Wait for the PolicyReport to appear
    for i in range(20):
        policy_report_response = subprocess.run(
            f"kubectl get policyreports -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if b"tcp-egress-restrictions-should-work" in policy_report_response.stdout:
            break
        time.sleep(1.3**i)
    assert b"tcp-egress-restrictions-should-work" in policy_report_response.stdout

    # Validate the summary: both rules should pass (one expected pass, one expected fail)
    summary_filter = "jsonpath='{.summary}'"
    policy_report_summary = subprocess.run(
        f"""kubectl get policyreport/tcp-egress-restrictions-should-work -n {k8s_namespace} -o {summary_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_summary = json.loads(policy_report_summary.stdout)
    assert policy_report_summary["pass"] >= 2

    # Validate the detailed results
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(
        f"""kubectl get policyreport/tcp-egress-restrictions-should-work -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_results = json.loads(policy_report_results_response.stdout)
    assert len(policy_report_results) == 2

    for result in policy_report_results:
        assert result["category"] == "tcp"
        assert result["result"] == "pass", str(result)
        assert result["source"] == "netchecks"

        test_spec = json.loads(result["properties"]["spec"])
        assert test_spec["type"] == "tcp"

        test_data = json.loads(result["properties"]["data"])
        if result["policy"] == "tcp-to-k8s-api-allowed":
            # Allowed by policy - connection should succeed
            assert test_data["connected"] is True
        elif result["policy"] == "tcp-to-blocked-port":
            # Blocked by Cilium policy - connection should fail
            assert test_data["connected"] is False
            assert test_data["error"] is not None

    # Clean up
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {tcp_restrictions_dir} --timeout=30s",
        shell=True,
        check=True,
    )
