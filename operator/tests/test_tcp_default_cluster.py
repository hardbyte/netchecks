import json
import time
import subprocess


def test_tcp_connectivity_with_installed_operator(netchecks, k8s_namespace, test_file_path):
    tcp_assertion_manifest = test_file_path("tcp-job.yaml")

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {tcp_assertion_manifest}",
        shell=True,
        check=True,
    )

    # Assert that a Job gets created in the same namespace
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl get jobs -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if b"tcp-should-work" in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    # Wait for the job to complete
    subprocess.run(
        f"kubectl wait Job/tcp-should-work -n {k8s_namespace} --for condition=complete --timeout=120s",
        shell=True,
        check=True,
    )

    # Assert that a PolicyReport gets created in the same namespace
    for i in range(10):
        policy_report_response = subprocess.run(
            f"kubectl get policyreports -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if b"tcp-should-work" in policy_report_response.stdout:
            break
        time.sleep(1.5**i)
    assert b"tcp-should-work" in policy_report_response.stdout

    summary_filter = "jsonpath='{.summary}'"
    policy_report_summary = subprocess.run(
        f"""kubectl get policyreport/tcp-should-work -n {k8s_namespace} -o {summary_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_summary = json.loads(policy_report_summary.stdout)

    assert policy_report_summary["pass"] >= 2

    # Now get the detailed policy report results
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(
        f"""kubectl get policyreport/tcp-should-work -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_results = json.loads(policy_report_results_response.stdout)

    for result in policy_report_results:
        assert result["category"] == "tcp"
        assert result["result"] == "pass"
        assert result["source"] == "netchecks"

        test_spec = json.loads(result["properties"]["spec"])
        assert test_spec["type"] == "tcp"

        test_data = json.loads(result["properties"]["data"])
        if result["policy"] == "tcp-to-k8s-api":
            assert test_data["connected"] is True
        elif result["policy"] == "tcp-to-nonexistent":
            assert test_data["connected"] is False

    # Delete the network assertion
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {tcp_assertion_manifest} --timeout=30s",
        shell=True,
        check=True,
    )
    time.sleep(3.0)
