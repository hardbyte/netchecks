import json
import time
import subprocess


def test_inline_context_data(netchecks, k8s_namespace, test_file_path):
    manifest = test_file_path("with-context-data.yaml")

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {manifest}",
        shell=True,
        check=True,
    )
    assertion_name = "http-with-inline-data"
    # Assert that a Job gets created in the same namespace
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl get jobs -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if assertion_name.encode() in jobs_response.stdout:
            break
        time.sleep(1.5**i)

    print("Job was created")
    # Wait for the job to complete
    subprocess.run(
        f"kubectl wait Job/{assertion_name} -n {k8s_namespace} --for condition=complete --timeout=60s",
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
        if assertion_name.encode() in policy_report_response.stdout:
            break
        time.sleep(1.5**i)
    assert assertion_name.encode() in policy_report_response.stdout
    print("Policy report was created")

    summary_filter = "jsonpath='{.summary}'"
    policy_report_summary = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {summary_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_summary = json.loads(policy_report_summary.stdout)

    assert policy_report_summary["pass"] >= 1
    assert "fail" not in policy_report_summary

    # Now get the detailed policy report results
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_results = json.loads(policy_report_results_response.stdout)

    for result in policy_report_results:
        assert result["category"] == "http"
        assert result["result"] == "pass"
        assert result["source"] == "netchecks"

        test_spec = json.loads(result["properties"]["spec"])
        assert test_spec["type"] == "http"
        assert test_spec["method"] == "get"

        test_data = json.loads(result["properties"]["data"])
        assert test_data["status-code"] == 200

        data = json.loads(test_data["body"])
        print(data)
        assert data["headers"]["X-Netcheck-Header"] == "yaml-data"

    # Delete the network assertion
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {manifest} --timeout=30s",
        shell=True,
        check=True,
    )
    time.sleep(3)
