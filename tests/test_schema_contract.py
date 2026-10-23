"""
Keep the Supabase schema and the order writer in sync.

The canonical contract (roadmap.txt, lines 160-174) is what the AI module
produces, the schema is what Supabase stores. They drifted once already: the
orders table had ``id``/``status``/``wilaya_code`` and no ``product_details``
column, so every order write was rejected by PostgREST. These tests read the
schema and fail as soon as the two disagree again.
"""
import re
from pathlib import Path

import pytest

from order_store import DERIVED_COLUMNS, ORDER_COLUMNS

SCHEMA = Path(__file__).resolve().parent.parent / "backend" / "schema.sql"


def read_schema():
    return SCHEMA.read_text(encoding="utf-8")


def table_body(schema, table):
    """Return the body of a CREATE TABLE statement."""
    match = re.search(
        rf"CREATE TABLE {table} \((.*?)\n\);",
        schema,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"CREATE TABLE {table} not found in {SCHEMA}"
    return match.group(1)


def column_names(schema, table):
    """List the columns of a table, ignoring the table constraints."""
    names = []
    for line in table_body(schema, table).splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        first = line.split()[0].rstrip(",")
        if first.upper() in {
            "PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE",
        }:
            continue
        names.append(first.lower())
    return names


def test_schema_file_exists():
    assert SCHEMA.exists(), f"missing {SCHEMA}"


def test_every_written_column_exists_in_the_orders_table():
    """The columns the store sends must exist, or PostgREST rejects the row."""
    columns = set(column_names(read_schema(), "orders"))
    missing = [column for column in ORDER_COLUMNS + DERIVED_COLUMNS
               if column not in columns]
    assert not missing, f"columns missing from the orders table: {missing}"


def test_the_orders_table_has_no_column_the_store_never_sends():
    """Extra NOT NULL columns without a default would break the insert."""
    body = table_body(read_schema(), "orders")
    columns = set(column_names(read_schema(), "orders"))
    written = set(ORDER_COLUMNS) | set(DERIVED_COLUMNS)
    for column in columns - written:
        definition = re.search(
            rf"^\s*{column}\s+([^\n]*)",
            body,
            re.IGNORECASE | re.MULTILINE,
        )
        assert definition, f"cannot read the definition of {column}"
        assert "NOT NULL" not in definition.group(1).upper(), (
            f"column {column} is NOT NULL but the store never sends it"
        )


def test_the_order_items_foreign_key_points_at_the_renamed_primary_key():
    """Renaming orders.id to orders.order_id must not leave a dangling FK."""
    schema = read_schema()
    assert "REFERENCES orders(id)" not in schema, (
        "order_items still references orders(id), the primary key is now order_id"
    )
    assert "order_id UUID REFERENCES orders(order_id)" in schema


def test_the_wilaya_range_is_enforced_on_the_code():
    """The name is free text, the code carries the 1-69 constraint."""
    body = table_body(read_schema(), "orders")
    assert "wilaya_code INT" in body
    assert re.search(r"wilaya_code >= 1 AND wilaya_code <= 69", body), (
        "the wilaya_code range check is missing"
    )


def test_the_conversation_state_enum_matches_the_code():
    """The service writes ESCALATION, the enum must accept it."""
    schema = read_schema()
    match = re.search(r"CREATE TYPE conversation_state AS ENUM \((.*?)\);",
                      schema, re.IGNORECASE | re.DOTALL)
    assert match, "conversation_state enum not found"
    values = {value.strip().strip("'") for value in match.group(1).split(",")}
    assert "ESCALATION" in values
    assert "ESCALATED" not in values, (
        "the enum still says ESCALATED, the service writes ESCALATION"
    )


def test_the_order_status_enum_accepts_every_status_the_code_writes():
    from schemas import OrderStatus

    schema = read_schema()
    match = re.search(r"CREATE TYPE order_status AS ENUM \((.*?)\);",
                      schema, re.IGNORECASE | re.DOTALL)
    assert match, "order_status enum not found"
    values = {value.strip().strip("'") for value in match.group(1).split(",")}
    missing = [status.value for status in OrderStatus if status.value not in values]
    assert not missing, f"order_status enum is missing {missing}"


@pytest.mark.parametrize("column", ORDER_COLUMNS)
def test_each_contract_column_is_in_the_schema(column):
    assert column in column_names(read_schema(), "orders")
