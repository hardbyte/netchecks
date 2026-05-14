---
title: PostgreSQL NetworkAssertions
description: Validate PostgreSQL connectivity, SQL assertions, and effective database grants.
---

PostgreSQL checks let Netchecks validate database access controls from the same runtime context as your workloads. They are useful as active controls alongside declarative role management tools such as `pgroles`: `pgroles` converges grants, while Netchecks independently verifies that the live database still enforces the expected access model.

## SQL Check

Use `type: postgres` to run a single SQL statement and validate the result with CEL:

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: postgres-sql-check
spec:
  context:
    - name: database
      secret:
        name: postgres-connection
  rules:
    - name: database-responds
      type: postgres
      dsn: "{{ database.DATABASE_URL }}"
      query: "select current_database() as database_name"
      validate:
        pattern: "data.success == true && size(data.rows) == 1"
        message: PostgreSQL should respond to a read-only SQL check.
```

By default SQL checks run in a read-only transaction and roll back afterwards.

### SQL Parameters

| Parameter | Description | Default |
| --- | --- | --- |
| `dsn` | PostgreSQL connection string | required |
| `query` | Single SQL statement to run | required |
| `params` | Optional positional or named query parameters | none |
| `timeout` | Connection and statement timeout in seconds | `5` |
| `read-only` | Run the transaction as read-only | `true` |
| `rollback` | Roll back after the statement | `true` |
| `row-limit` | Maximum rows returned in `data.rows` | `100` |

The result data includes `success`, `row-count`, `columns`, `rows`, `startTimestamp`, and `endTimestamp`. On errors it also includes `exception-type`, `exception`, and `sqlstate` when PostgreSQL reports one.

## Grant Check

Use `type: postgres-grants` to validate effective privileges. These checks use PostgreSQL's `has_*_privilege` functions, so they account for role membership and `PUBLIC` grants rather than only inspecting raw ACL arrays.

```yaml
apiVersion: netchecks.io/v1
kind: NetworkAssertion
metadata:
  name: postgres-grant-controls
spec:
  context:
    - name: database
      secret:
        name: postgres-connection
  rules:
    - name: billing-schema-is-team-only
      type: postgres-grants
      dsn: "{{ database.DATABASE_URL }}"
      rules:
        - name: non-billing-login-roles-cannot-use-billing
          mode: deny
          roles:
            login: true
            exclude-member-of: [team_billing]
          objects:
            type: schema
            names: [billing]
          privileges: [USAGE, CREATE]
      validate:
        pattern: "data.success == true && data['violation-count'] == 0"
        message: Only team_billing members should access the billing schema.
```

Another example checks that an application role cannot truncate billing tables:

```yaml
    - name: payments-app-cannot-truncate
      type: postgres-grants
      dsn: "{{ database.DATABASE_URL }}"
      rules:
        - name: payments-app-no-truncate
          mode: deny
          roles:
            names: [payments_app]
          objects:
            type: table
            schemas: [billing]
            names: ["*"]
          privileges: [TRUNCATE]
```

Grant check rules support `mode: deny` and `mode: require`. A deny rule reports a violation when a selected role has the selected privilege. A require rule reports a violation when a selected role lacks the selected privilege.

### Grant Rule Selectors

Role selectors:

| Field | Description |
| --- | --- |
| `names` | Explicit role names |
| `login` | Select login or non-login roles |
| `member-of` | Select roles that are members of these roles |
| `exclude-member-of` | Exclude roles that are members of these roles |
| `exclude` | Explicit role names to exclude |
| `include-system-roles` | Include roles whose names start with `pg_` |

Object selectors:

| Object type | Selector fields | Privileges |
| --- | --- | --- |
| `database` | `names` | `CONNECT`, `CREATE`, `TEMPORARY`, `TEMP` |
| `schema` | `names` | `USAGE`, `CREATE` |
| `table` | `schemas`, `names` | `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER` — covers ordinary tables, partitioned tables, views, materialized views, and foreign tables |
| `sequence` | `schemas`, `names` | `USAGE`, `SELECT`, `UPDATE` |
| `function` | `schemas`, `names` | `EXECUTE` |

Use `"*"` in `names` or `schemas` to select all non-system objects of that type.

## Active Negative Checks

For some controls you may want to prove that an operation fails when run as an application role. Use the generic SQL check with that role's connection string:

```yaml
    - name: payments-app-cannot-create-table
      type: postgres
      dsn: "{{ payments_app.DATABASE_URL }}"
      query: "create table billing.netcheck_ddl_probe(id integer)"
      read-only: false
      rollback: true
      validate:
        pattern: "data.success == false && data.sqlstate == '42501'"
        message: payments_app must not be able to create tables in billing.
```

Prefer catalog-based `postgres-grants` checks for destructive privileges such as `TRUNCATE`. If you use active checks, target dedicated probe objects and keep `rollback: true` unless the check explicitly needs to commit.

## Least Privilege for the Probe Role

**Important:** Grant the probe role only the privileges it needs. Using a superuser or a role with
`pg_execute_server_program` membership is strongly discouraged.

`COPY ... TO PROGRAM 'cmd'` runs a shell command on the database server. PostgreSQL allows this for
superusers and roles with the `pg_execute_server_program` system role. A `read-only` transaction
does not prevent it because `COPY TO` is classified as a read from the transaction's perspective.
If your probe role is a superuser, a misconfigured or injected query could execute arbitrary shell
commands on the database server.

Create a dedicated role with only the access the probe needs:

```sql
CREATE ROLE netcheck_probe WITH LOGIN PASSWORD '...';
-- allow connecting to the database being monitored
GRANT CONNECT ON DATABASE myapp TO netcheck_probe;
-- grant only the catalog access needed for grant checks
GRANT USAGE ON SCHEMA information_schema TO netcheck_probe;
-- for SQL checks: grant SELECT on specific tables/views, nothing else
GRANT SELECT ON myapp.orders TO netcheck_probe;
```

A non-superuser role without `pg_execute_server_program` will receive a permission-denied error
from `COPY ... TO PROGRAM`, `COPY ... FROM PROGRAM`, and similar server-side file operations.

### Sequences and non-transactional side effects

`nextval()` advances a sequence even when the transaction is rolled back. Avoid calling `nextval()`
in probe queries. The `read-only: true` default will block `nextval()` anyway, but be cautious if
you set `read-only: false` with `rollback: true`.

## Redaction

Netchecks redacts `dsn`, `params`, `password`, and `connection` fields from probe output by default. Use `--disable-redaction` only when debugging locally.
