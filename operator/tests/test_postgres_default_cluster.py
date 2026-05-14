import json
import shlex
import subprocess
import time


def test_postgres_grants_with_installed_operator(netchecks, k8s_namespace, test_file_path):
    database_namespace = "database"
    postgres_db_manifest = test_file_path("postgres-db.yaml")
    postgres_assertion_manifest = test_file_path("postgres-grants.yaml")

    subprocess.run(
        f"kubectl create namespace {database_namespace} --dry-run=client -o yaml | kubectl apply -f -",
        shell=True,
        check=True,
    )
    subprocess.run(f"kubectl apply -n {database_namespace} -f {postgres_db_manifest}", shell=True, check=True)
    subprocess.run(
        f"kubectl wait Deployment/postgres -n {database_namespace} --for condition=Available --timeout=120s",
        shell=True,
        check=True,
    )
    _initialize_postgres(database_namespace)

    subprocess.run(
        f"kubectl apply -n {k8s_namespace} -f {postgres_assertion_manifest}",
        shell=True,
        check=True,
    )

    assertion_name = "postgres-grants-should-work"
    _wait_for_job(assertion_name, k8s_namespace)
    _wait_for_policy_report(assertion_name, k8s_namespace)

    summary = _get_policy_report_summary(assertion_name, k8s_namespace)
    assert summary["pass"] == 2
    assert "fail" not in summary

    results = _get_policy_report_results(assertion_name, k8s_namespace)
    categories = {result["category"] for result in results}
    assert categories == {"postgres", "postgres-grants"}

    for result in results:
        assert result["result"] == "pass"
        test_spec = json.loads(result["properties"]["spec"])
        assert test_spec["dsn"] == "REDACTED"

    subprocess.run(
        f"kubectl delete -n {k8s_namespace} -f {postgres_assertion_manifest} --timeout=30s",
        shell=True,
        check=True,
    )
    time.sleep(3.0)


def _initialize_postgres(database_namespace):
    sql = """
    do $$
    begin
      if not exists (select 1 from pg_roles where rolname = 'payments_app') then
        create role payments_app;
      end if;
    end
    $$;
    create schema if not exists billing;
    create table if not exists billing.invoices(id integer);
    revoke all on schema billing from payments_app;
    revoke all on table billing.invoices from payments_app;
    """
    subprocess.run(
        f"kubectl exec -n {database_namespace} deployment/postgres -- psql -U netcheck -d netcheck -v ON_ERROR_STOP=1 -c {shlex.quote(sql)}",
        shell=True,
        check=True,
    )


def _wait_for_job(assertion_name, k8s_namespace):
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

    subprocess.run(
        f"kubectl wait Job/{assertion_name} -n {k8s_namespace} --for condition=complete --timeout=120s",
        shell=True,
        check=True,
    )


def _wait_for_policy_report(assertion_name, k8s_namespace):
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


def _get_policy_report_summary(assertion_name, k8s_namespace):
    summary_filter = "jsonpath='{.summary}'"
    policy_report_summary = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {summary_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    return json.loads(policy_report_summary.stdout)


def _get_policy_report_results(assertion_name, k8s_namespace):
    results_filter = "jsonpath='{.results}'"
    policy_report_results = subprocess.run(
        f"""kubectl get policyreport/{assertion_name} -n {k8s_namespace} -o {results_filter}""",
        shell=True,
        check=True,
        capture_output=True,
    )
    return json.loads(policy_report_results.stdout)
