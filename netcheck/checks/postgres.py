import datetime
import decimal
import logging
from typing import Any, Optional
import uuid

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("netcheck.postgres")

DEFAULT_POSTGRES_VALIDATION_RULE = """
data.success == true
"""

DEFAULT_POSTGRES_GRANTS_VALIDATION_RULE = """
data.success == true && data['violation-count'] == 0
"""

GRANTABLE_PRIVILEGES = {
    "database": {"CONNECT", "CREATE", "TEMPORARY", "TEMP"},
    "schema": {"USAGE", "CREATE"},
    "table": {"SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"},
    "sequence": {"USAGE", "SELECT", "UPDATE"},
    "function": {"EXECUTE"},
}


def postgres_query_check(
    dsn: str,
    query: str,
    params: Optional[list[Any] | dict[str, Any]] = None,
    timeout: float = 5,
    read_only: bool = True,
    rollback: bool = True,
    row_limit: int = 100,
) -> dict:
    test_spec = {
        "type": "postgres",
        "dsn": dsn,
        "query": query,
        "params": params,
        "timeout": timeout,
        "read-only": read_only,
        "rollback": rollback,
        "row-limit": row_limit,
    }
    result_data = {
        "startTimestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    output = {"spec": test_spec, "data": result_data}

    try:
        statement = _single_statement(query)
        result = _execute_query(
            dsn=dsn,
            query=statement,
            params=params,
            timeout=timeout,
            read_only=read_only,
            rollback=rollback,
            row_limit=row_limit,
        )
        result_data.update(result)
        result_data["success"] = True
    except Exception as error:
        logger.debug("Postgres check failed", exc_info=error)
        result_data["success"] = False
        result_data["exception-type"] = error.__class__.__name__
        result_data["exception"] = str(error)
        sqlstate = getattr(error, "sqlstate", None)
        if sqlstate is not None:
            result_data["sqlstate"] = sqlstate

    result_data["endTimestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
    return output


def postgres_grants_check(
    dsn: str,
    rules: list[dict[str, Any]],
    timeout: float = 5,
) -> dict:
    test_spec = {
        "type": "postgres-grants",
        "dsn": dsn,
        "rules": rules,
        "timeout": timeout,
    }
    result_data = {
        "startTimestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "rule-count": len(rules),
        "violations": [],
    }
    output = {"spec": test_spec, "data": result_data}

    try:
        with psycopg.connect(dsn, connect_timeout=max(1, int(timeout)), row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select set_config('statement_timeout', %s, true)", (str(max(1, int(timeout * 1000))),))
                for rule in rules:
                    result_data["violations"].extend(_evaluate_grant_rule(cursor, rule))
                connection.rollback()
        result_data["success"] = True
    except Exception as error:
        logger.debug("Postgres grants check failed", exc_info=error)
        result_data["success"] = False
        result_data["exception-type"] = error.__class__.__name__
        result_data["exception"] = str(error)
        sqlstate = getattr(error, "sqlstate", None)
        if sqlstate is not None:
            result_data["sqlstate"] = sqlstate

    result_data["violation-count"] = len(result_data["violations"])
    result_data["endTimestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
    return output


def _single_statement(query: str) -> str:
    statement = query.strip()
    if not statement:
        raise ValueError("query must not be empty")
    without_trailing_semicolon = statement[:-1] if statement.endswith(";") else statement
    if ";" in without_trailing_semicolon:
        raise ValueError("postgres checks only support a single SQL statement")
    return statement


def _execute_query(
    dsn: str,
    query: str,
    params: Optional[list[Any] | dict[str, Any]],
    timeout: float,
    read_only: bool,
    rollback: bool,
    row_limit: int,
) -> dict:
    with psycopg.connect(dsn, connect_timeout=max(1, int(timeout)), row_factory=dict_row) as connection:
        connection.read_only = read_only
        with connection.cursor() as cursor:
            cursor.execute("select set_config('statement_timeout', %s, true)", (str(max(1, int(timeout * 1000))),))
            cursor.execute(query, params)

            rows = []
            columns = []
            if cursor.description is not None:
                columns = [column.name for column in cursor.description]
                rows = [_jsonable(row) for row in cursor.fetchmany(row_limit)]

            row_count = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else len(rows)

        if rollback:
            connection.rollback()
        else:
            connection.commit()

    return {
        "row-count": row_count,
        "columns": columns,
        "rows": rows,
    }


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _evaluate_grant_rule(cursor, rule: dict[str, Any]) -> list[dict[str, Any]]:
    rule_name = rule.get("name", "unnamed")
    mode = rule.get("mode", "deny")
    if mode not in {"deny", "require"}:
        raise ValueError(f"postgres-grants rule '{rule_name}' has unsupported mode '{mode}'")

    object_selector = rule.get("objects", {})
    object_type = object_selector.get("type")
    if object_type not in GRANTABLE_PRIVILEGES:
        raise ValueError(f"postgres-grants rule '{rule_name}' has unsupported object type '{object_type}'")

    privileges = [privilege.upper() for privilege in rule.get("privileges", [])]
    if not privileges:
        raise ValueError(f"postgres-grants rule '{rule_name}' must specify privileges")
    unsupported = sorted(set(privileges) - GRANTABLE_PRIVILEGES[object_type])
    if unsupported:
        raise ValueError(
            f"postgres-grants rule '{rule_name}' has unsupported {object_type} privileges: {', '.join(unsupported)}"
        )

    role_names = _selected_roles(cursor, rule.get("roles", {}))
    objects = _selected_objects(cursor, object_type, object_selector)

    violations = []
    for role_name in role_names:
        for object_ref in objects:
            for privilege in privileges:
                has_privilege = _has_privilege(cursor, role_name, object_type, object_ref["identity"], privilege)
                if (mode == "deny" and has_privilege) or (mode == "require" and not has_privilege):
                    violations.append(
                        {
                            "rule": rule_name,
                            "role": role_name,
                            "object-type": object_type,
                            "schema": object_ref.get("schema"),
                            "object": object_ref["name"],
                            "privilege": privilege,
                            "expected": "absent" if mode == "deny" else "present",
                        }
                    )

    return violations


def _selected_roles(cursor, selector: dict[str, Any]) -> list[str]:
    requested_names = selector.get("names")
    include_system_roles = bool(selector.get("include-system-roles", False))
    exclude_names = set(selector.get("exclude", []))
    member_of = selector.get("member-of", [])
    exclude_member_of = selector.get("exclude-member-of", [])

    conditions = []
    params: list[Any] = []
    if requested_names:
        conditions.append("r.rolname = any(%s)")
        params.append(requested_names)
    if "login" in selector:
        conditions.append("r.rolcanlogin = %s")
        params.append(bool(selector["login"]))
    if not include_system_roles:
        conditions.append("r.rolname !~ '^pg_'")
    if exclude_names:
        conditions.append("not r.rolname = any(%s)")
        params.append(list(exclude_names))
    for parent_role in member_of:
        conditions.append("pg_has_role(r.rolname, %s, 'member')")
        params.append(parent_role)
    for parent_role in exclude_member_of:
        conditions.append("not pg_has_role(r.rolname, %s, 'member')")
        params.append(parent_role)

    where_clause = " and ".join(conditions) if conditions else "true"
    cursor.execute(f"select r.rolname from pg_roles r where {where_clause} order by r.rolname", params)
    return [row["rolname"] for row in cursor.fetchall()]


def _selected_objects(cursor, object_type: str, selector: dict[str, Any]) -> list[dict[str, Any]]:
    match object_type:
        case "database":
            return _selected_databases(cursor, selector)
        case "schema":
            return _selected_schemas(cursor, selector)
        case "table":
            return _selected_relations(cursor, selector, relation_kinds=["r", "p"])
        case "sequence":
            return _selected_relations(cursor, selector, relation_kinds=["S"])
        case "function":
            return _selected_functions(cursor, selector)
        case _:
            raise ValueError(f"unsupported object type '{object_type}'")


def _selected_databases(cursor, selector: dict[str, Any]) -> list[dict[str, Any]]:
    names = selector.get("names")
    params = []
    where_clause = "datallowconn"
    if names and names != ["*"]:
        where_clause += " and datname = any(%s)"
        params.append(names)
    cursor.execute(f"select datname from pg_database where {where_clause} order by datname", params)
    return [{"name": row["datname"], "identity": row["datname"]} for row in cursor.fetchall()]


def _selected_schemas(cursor, selector: dict[str, Any]) -> list[dict[str, Any]]:
    names = selector.get("names")
    params = []
    conditions = ["left(nspname, 3) <> 'pg_'", "nspname <> 'information_schema'"]
    if names and names != ["*"]:
        conditions.append("nspname = any(%s)")
        params.append(names)
    cursor.execute(
        f"select nspname from pg_namespace where {' and '.join(conditions)} order by nspname",
        params,
    )
    return [{"name": row["nspname"], "identity": row["nspname"]} for row in cursor.fetchall()]


def _selected_relations(cursor, selector: dict[str, Any], relation_kinds: list[str]) -> list[dict[str, Any]]:
    schemas = selector.get("schemas")
    names = selector.get("names")
    params: list[Any] = [relation_kinds]
    conditions = ["c.relkind = any(%s)", "left(n.nspname, 3) <> 'pg_'", "n.nspname <> 'information_schema'"]
    if schemas and schemas != ["*"]:
        conditions.append("n.nspname = any(%s)")
        params.append(schemas)
    if names and names != ["*"]:
        conditions.append("c.relname = any(%s)")
        params.append(names)
    cursor.execute(
        f"""
        select n.nspname as schema_name, c.relname, c.oid::regclass::text as identity
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where {" and ".join(conditions)}
        order by n.nspname, c.relname
        """,
        params,
    )
    return [
        {"schema": row["schema_name"], "name": row["relname"], "identity": row["identity"]} for row in cursor.fetchall()
    ]


def _selected_functions(cursor, selector: dict[str, Any]) -> list[dict[str, Any]]:
    schemas = selector.get("schemas")
    names = selector.get("names")
    params = []
    conditions = ["left(n.nspname, 3) <> 'pg_'", "n.nspname <> 'information_schema'"]
    if schemas and schemas != ["*"]:
        conditions.append("n.nspname = any(%s)")
        params.append(schemas)
    if names and names != ["*"]:
        conditions.append("p.proname = any(%s)")
        params.append(names)
    cursor.execute(
        f"""
        select n.nspname as schema_name, p.proname, p.oid::regprocedure::text as identity
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where {" and ".join(conditions)}
        order by n.nspname, p.proname, p.oid
        """,
        params,
    )
    return [
        {"schema": row["schema_name"], "name": row["proname"], "identity": row["identity"]} for row in cursor.fetchall()
    ]


def _has_privilege(cursor, role_name: str, object_type: str, object_identity: str, privilege: str) -> bool:
    function_name = {
        "database": "has_database_privilege",
        "schema": "has_schema_privilege",
        "table": "has_table_privilege",
        "sequence": "has_sequence_privilege",
        "function": "has_function_privilege",
    }[object_type]
    cursor.execute(f"select {function_name}(%s, %s, %s) as allowed", (role_name, object_identity, privilege))
    return bool(cursor.fetchone()["allowed"])
