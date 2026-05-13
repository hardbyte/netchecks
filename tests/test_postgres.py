import os
from unittest.mock import Mock

import pytest

import netcheck.runner as netcheck_runner
from netcheck.checks import postgres as postgres_checks
from netcheck.checks.postgres import postgres_grants_check, postgres_query_check
from netcheck.runner import check_individual_assertion


def test_postgres_query_check_rejects_multiple_statements():
    result = postgres_query_check("postgres://example", "select 1; select 2")

    assert result["data"]["success"] is False
    assert result["data"]["exception-type"] == "ValueError"
    assert "single SQL statement" in result["data"]["exception"]


def test_postgres_query_check_rejects_empty_statement():
    result = postgres_query_check("postgres://example", "  ")

    assert result["data"]["success"] is False
    assert result["data"]["exception-type"] == "ValueError"
    assert "query must not be empty" in result["data"]["exception"]


def test_postgres_query_check_default_output_with_mocked_connection(monkeypatch):
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.description = [Mock(name="answer")]
    cursor.description[0].name = "answer"
    cursor.fetchmany.return_value = [{"answer": 42}]
    cursor.rowcount = 1

    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    connection.cursor.return_value = cursor

    connect = Mock(return_value=connection)
    monkeypatch.setattr(postgres_checks.psycopg, "connect", connect)

    result = postgres_query_check("postgres://example", "select 42 as answer")

    assert result["spec"]["type"] == "postgres"
    assert result["data"]["success"] is True
    assert result["data"]["row-count"] == 1
    assert result["data"]["rows"] == [{"answer": 42}]
    assert connection.read_only is True
    connection.rollback.assert_called_once()
    connect.assert_called_once_with("postgres://example", connect_timeout=5, row_factory=postgres_checks.dict_row)


def test_postgres_grants_deny_rule_reports_effective_privilege_violation(monkeypatch):
    responses = {
        "select r.rolname": [{"rolname": "payments_app"}],
        "select n.nspname as schema_name, c.relname": [
            {"schema_name": "billing", "relname": "invoices", "identity": "billing.invoices"}
        ],
        "select has_table_privilege": [{"allowed": True}],
    }
    cursor = _fake_cursor(responses)
    connection = _fake_connection(cursor)
    monkeypatch.setattr(postgres_checks.psycopg, "connect", Mock(return_value=connection))

    result = postgres_grants_check(
        "postgres://example",
        [
            {
                "name": "payments-app-cannot-truncate",
                "mode": "deny",
                "roles": {"names": ["payments_app"]},
                "objects": {"type": "table", "schemas": ["billing"], "names": ["*"]},
                "privileges": ["TRUNCATE"],
            }
        ],
    )

    assert result["data"]["success"] is True
    assert result["data"]["violation-count"] == 1
    assert result["data"]["violations"] == [
        {
            "rule": "payments-app-cannot-truncate",
            "role": "payments_app",
            "object-type": "table",
            "schema": "billing",
            "object": "invoices",
            "privilege": "TRUNCATE",
            "expected": "absent",
        }
    ]


def test_postgres_grants_deny_rule_without_effective_privilege_has_no_violations(monkeypatch):
    responses = {
        "select r.rolname": [{"rolname": "payments_app"}],
        "select n.nspname as schema_name, c.relname": [
            {"schema_name": "billing", "relname": "invoices", "identity": "billing.invoices"}
        ],
        "select has_table_privilege": [{"allowed": False}],
    }
    cursor = _fake_cursor(responses)
    connection = _fake_connection(cursor)
    monkeypatch.setattr(postgres_checks.psycopg, "connect", Mock(return_value=connection))

    result = postgres_grants_check(
        "postgres://example",
        [
            {
                "name": "payments-app-cannot-truncate",
                "mode": "deny",
                "roles": {"names": ["payments_app"]},
                "objects": {"type": "table", "schemas": ["billing"], "names": ["*"]},
                "privileges": ["TRUNCATE"],
            }
        ],
    )

    assert result["data"]["success"] is True
    assert result["data"]["violation-count"] == 0
    assert result["data"]["violations"] == []


def test_postgres_grants_require_rule_reports_missing_privilege(monkeypatch):
    responses = {
        "select r.rolname": [{"rolname": "billing_reader"}],
        "select nspname from pg_namespace": [{"nspname": "billing"}],
        "select has_schema_privilege": [{"allowed": False}],
    }
    cursor = _fake_cursor(responses)
    connection = _fake_connection(cursor)
    monkeypatch.setattr(postgres_checks.psycopg, "connect", Mock(return_value=connection))

    result = postgres_grants_check(
        "postgres://example",
        [
            {
                "name": "billing-reader-needs-schema-usage",
                "mode": "require",
                "roles": {"names": ["billing_reader"]},
                "objects": {"type": "schema", "names": ["billing"]},
                "privileges": ["USAGE"],
            }
        ],
    )

    assert result["data"]["success"] is True
    assert result["data"]["violation-count"] == 1
    assert result["data"]["violations"][0]["expected"] == "present"


def test_postgres_grants_invalid_rule_returns_failed_check(monkeypatch):
    cursor = _fake_cursor({})
    connection = _fake_connection(cursor)
    monkeypatch.setattr(postgres_checks.psycopg, "connect", Mock(return_value=connection))

    result = postgres_grants_check(
        "postgres://example",
        [
            {
                "name": "invalid-table-privilege",
                "mode": "deny",
                "roles": {"names": ["payments_app"]},
                "objects": {"type": "table", "schemas": ["billing"], "names": ["*"]},
                "privileges": ["CREATE"],
            }
        ],
    )

    assert result["data"]["success"] is False
    assert result["data"]["exception-type"] == "ValueError"
    assert "unsupported table privileges: CREATE" in result["data"]["exception"]


def test_runner_redacts_postgres_dsn_and_params(monkeypatch):
    monkeypatch.setattr(
        netcheck_runner,
        "postgres_query_check",
        lambda **kwargs: {
            "spec": {"type": "postgres", "dsn": kwargs["dsn"], "params": kwargs["params"]},
            "data": {"success": True},
        },
    )

    result = check_individual_assertion(
        "postgres",
        {
            "type": "postgres",
            "dsn": "postgres://user:secret@example/db",
            "query": "select %s",
            "params": ["secret"],
        },
        err_console=Mock(),
    )

    assert result["status"] == "pass"
    assert result["spec"]["dsn"] == "REDACTED"
    assert result["spec"]["params"] == "REDACTED"


@pytest.mark.skipif(not os.environ.get("NETCHECK_POSTGRES_DSN"), reason="NETCHECK_POSTGRES_DSN is not set")
def test_postgres_query_check_with_real_postgres():
    result = postgres_query_check(os.environ["NETCHECK_POSTGRES_DSN"], "select 42 as answer")

    assert result["data"]["success"] is True, result
    assert result["data"]["rows"] == [{"answer": 42}]


@pytest.mark.skipif(not os.environ.get("NETCHECK_POSTGRES_DSN"), reason="NETCHECK_POSTGRES_DSN is not set")
def test_postgres_query_check_with_real_postgres_read_only_negative_control():
    result = postgres_query_check(
        os.environ["NETCHECK_POSTGRES_DSN"],
        "create table netcheck_read_only_probe(id integer)",
    )

    assert result["data"]["success"] is False, result
    assert result["data"].get("sqlstate") == "25006"


@pytest.mark.skipif(not os.environ.get("NETCHECK_POSTGRES_DSN"), reason="NETCHECK_POSTGRES_DSN is not set")
def test_postgres_grants_check_with_real_postgres():
    import psycopg

    dsn = os.environ["NETCHECK_POSTGRES_DSN"]
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("drop schema if exists netcheck_grants_probe cascade")
            cursor.execute("drop role if exists netcheck_grants_probe_role")
            cursor.execute("create role netcheck_grants_probe_role")
            cursor.execute("create schema netcheck_grants_probe")
            cursor.execute("create table netcheck_grants_probe.invoices(id integer)")
            cursor.execute("grant usage on schema netcheck_grants_probe to netcheck_grants_probe_role")

    try:
        require_result = postgres_grants_check(
            dsn,
            [
                {
                    "name": "probe-role-has-schema-usage",
                    "mode": "require",
                    "roles": {"names": ["netcheck_grants_probe_role"]},
                    "objects": {"type": "schema", "names": ["netcheck_grants_probe"]},
                    "privileges": ["USAGE"],
                }
            ],
        )
        assert require_result["data"]["success"] is True, require_result
        assert require_result["data"]["violation-count"] == 0

        deny_result = postgres_grants_check(
            dsn,
            [
                {
                    "name": "probe-role-cannot-truncate",
                    "mode": "deny",
                    "roles": {"names": ["netcheck_grants_probe_role"]},
                    "objects": {"type": "table", "schemas": ["netcheck_grants_probe"], "names": ["*"]},
                    "privileges": ["TRUNCATE"],
                }
            ],
        )
        assert deny_result["data"]["success"] is True, deny_result
        assert deny_result["data"]["violation-count"] == 0

        with psycopg.connect(dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("grant truncate on table netcheck_grants_probe.invoices to netcheck_grants_probe_role")

        violated_deny_result = postgres_grants_check(
            dsn,
            [
                {
                    "name": "probe-role-cannot-truncate",
                    "mode": "deny",
                    "roles": {"names": ["netcheck_grants_probe_role"]},
                    "objects": {"type": "table", "schemas": ["netcheck_grants_probe"], "names": ["*"]},
                    "privileges": ["TRUNCATE"],
                }
            ],
        )
        assert violated_deny_result["data"]["success"] is True, violated_deny_result
        assert violated_deny_result["data"]["violation-count"] == 1
    finally:
        with psycopg.connect(dsn, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("drop schema if exists netcheck_grants_probe cascade")
                cursor.execute("drop role if exists netcheck_grants_probe_role")


def _fake_cursor(responses):
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor._last_sql = ""

    def execute(sql, params=None):
        cursor._last_sql = " ".join(sql.split())

    def fetchall():
        return _response_for_sql(responses, cursor._last_sql)

    def fetchone():
        return _response_for_sql(responses, cursor._last_sql)[0]

    cursor.execute.side_effect = execute
    cursor.fetchall.side_effect = fetchall
    cursor.fetchone.side_effect = fetchone
    return cursor


def _fake_connection(cursor):
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    connection.cursor.return_value = cursor
    return connection


def _response_for_sql(responses, sql):
    for prefix, response in responses.items():
        if sql.startswith(prefix):
            return response
    return [{"set_config": "5s"}]
