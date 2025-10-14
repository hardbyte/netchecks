import json
import time
import subprocess


def test_use_external_config_map_data(netchecks, k8s_namespace, test_file_path):
    manifest = test_file_path("with-configmap-data.yaml")

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {manifest}",
        shell=True,
        check=True,
    )
    assertion_name = "http-with-external-data"
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

    # Wait for the job to complete
    wait_result = subprocess.run(
        f"kubectl wait Job/{assertion_name} -n {k8s_namespace} --for condition=complete --timeout=120s",
        shell=True,
        capture_output=True,
    )
    if wait_result.returncode != 0:
        # Get pod logs to help debug the failure
        print(f"\n=== Job wait failed. Capturing pod logs for debugging ===")
        print(f"Wait command stderr: {wait_result.stderr.decode()}")

        # Get all pods for this job
        pods_result = subprocess.run(
            f"kubectl get pods -n {k8s_namespace} -l job-name={assertion_name} -o name",
            shell=True,
            capture_output=True,
        )
        pod_names = pods_result.stdout.decode().strip().split('\n')

        for pod_name in pod_names:
            if pod_name:
                pod_name = pod_name.replace('pod/', '')
                print(f"\n=== Logs from {pod_name} ===")
                logs_result = subprocess.run(
                    f"kubectl logs {pod_name} -n {k8s_namespace}",
                    shell=True,
                    capture_output=True,
                )
                print(logs_result.stdout.decode())
                if logs_result.stderr:
                    print(f"Stderr: {logs_result.stderr.decode()}")

                # Also get pod describe for more details
                print(f"\n=== Describe {pod_name} ===")
                describe_result = subprocess.run(
                    f"kubectl describe pod {pod_name} -n {k8s_namespace}",
                    shell=True,
                    capture_output=True,
                )
                print(describe_result.stdout.decode())

        # Re-raise the error
        wait_result.check_returncode()

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

        # Test data should be a string containing JSON returned by the server which should include the header
        # we injected from the configmap
        data = json.loads(test_data["body"])
        assert data["headers"]["X-Netcheck-Header"] == "some-data-from-a-configmap!"

    # Delete the network assertion
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {manifest} --timeout=30s",
        shell=True,
        check=True,
    )


def test_use_external_config_map_data_with_formatted_data(netchecks, k8s_namespace, test_file_path):
    manifest = test_file_path("with-configmap-json-yaml-data.yaml")

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {manifest}",
        shell=True,
        check=True,
    )
    assertion_name = "http-with-external-data-formats"
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

    # Wait for the job to complete
    subprocess.run(
        f"kubectl wait Job/{assertion_name} -n {k8s_namespace} --for condition=complete --timeout=120s",
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

        # Test data should be a string containing JSON returned by the server which should include the header
        # we injected from the configmap
        json.loads(test_data["body"])

    # Delete the network assertion
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {manifest} --timeout=30s",
        shell=True,
        check=True,
    )
