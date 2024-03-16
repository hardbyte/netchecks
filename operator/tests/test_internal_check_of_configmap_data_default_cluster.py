import json
import time
import subprocess


def test_internal_check(netchecks, k8s_namespace, test_file_path):
    na_manifest = test_file_path("internal-config-map-check.yaml")
    cm_manifest_foo = test_file_path("some-config-map-foo.yaml")
    cm_manifest_bar = test_file_path("some-config-map-bar.yaml")

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {cm_manifest_bar} -f {na_manifest}",
        shell=True,
        check=True,
    )
    assertion_name = "internal-k8s-config-check"

    # Assert that a CronJob gets created in the same namespace
    _assert_cronjob_created(assertion_name, k8s_namespace)

    _trigger_re_evaluation_of_assertion(assertion_name, k8s_namespace, 'a')

    # Assert that a Job gets created in the same namespace
    _assert_job_created(assertion_name+'-a', k8s_namespace)

    # Wait for the job to complete
    subprocess.run(
        f"kubectl wait Job/{assertion_name}-a -n {k8s_namespace} --for condition=complete --timeout=60s",
        shell=True,
        check=True,
    )

    # Assert that a PolicyReport gets created in the same namespace
    _assert_policy_report_present(assertion_name, k8s_namespace)

    # Get the detailed policy report results
    summary = _get_policy_report_summary(assertion_name, k8s_namespace)
    print(summary)
    assert summary["pass"] == 1
    policy_report_results = _get_policy_report_results(assertion_name, k8s_namespace)

    for result in policy_report_results:
        assert result["category"] == "internal"
        assert result["result"] == "pass"
        assert result["source"] == "netchecks"

    # Update the config map to the failing case
    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {cm_manifest_foo}",
        shell=True,
        check=True,
    )

    # Manually trigger a re-evaluation of the assertion
    suffix = 'b'
    _trigger_re_evaluation_of_assertion(assertion_name, k8s_namespace, suffix)

    # Assert that a Job gets created in the same namespace
    _assert_job_created(assertion_name + suffix, k8s_namespace)
    print("waiting for job completion")
    subprocess.run(
        f"kubectl wait Job/{assertion_name}-{suffix} -n {k8s_namespace} --for condition=complete --timeout=60s",
        shell=True,
        check=True,
    )

    # Assert that the Policy Report includes the failing result

    summary = _get_policy_report_summary(assertion_name, k8s_namespace)
    assert summary["fail"] == 1
    assert "pass" not in summary

    policy_report_results = _get_policy_report_results(assertion_name, k8s_namespace)

    # Delete the network assertion
    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {na_manifest} --timeout=30s",
        shell=True,
        check=True,
    )
    time.sleep(3)


def _get_policy_report_results(assertion_name, k8s_namespace):
    results_filter = "jsonpath='{.results}'"
    policy_report_results_response = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_results = json.loads(policy_report_results_response.stdout)
    return policy_report_results


def _get_policy_report_summary(assertion_name, k8s_namespace):
    results_filter = "jsonpath='{.summary}'"
    policy_report_results_response = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    policy_report_results = json.loads(policy_report_results_response.stdout)
    return policy_report_results


def _assert_policy_report_present(assertion_name, k8s_namespace):
    for i in range(10):
        policy_report_response = subprocess.run(
            f"kubectl get policyreports -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if assertion_name.encode() in policy_report_response.stdout:
            break
        time.sleep(1.5 ** i)
    assert assertion_name.encode() in policy_report_response.stdout


def _assert_job_created(job_name, k8s_namespace):
    print("Checking job creation for ", job_name)
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl get jobs -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if job_name.encode() in jobs_response.stdout:
            break
        time.sleep(1.5 ** i)


def _assert_cronjob_created(assertion_name, k8s_namespace):
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl get cronjobs -n {k8s_namespace}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if assertion_name.encode() in jobs_response.stdout:
            break
        time.sleep(1.5 ** i)


def _trigger_re_evaluation_of_assertion(assertion_name, k8s_namespace, manual_trigger_suffix='manual-trigger'):
    for i in range(10):
        jobs_response = subprocess.run(
            f"kubectl create job --from=cronjob/{assertion_name} -n {k8s_namespace} {assertion_name}-{manual_trigger_suffix}",
            shell=True,
            check=True,
            capture_output=True,
        )
        if "created".encode() in jobs_response.stdout:
            break
        time.sleep(1.5 ** i)
