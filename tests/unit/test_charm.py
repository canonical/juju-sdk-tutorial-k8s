#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
import ops
from ops import testing

from charm import FastAPIDemoCharm


def test_pebble_layer():
    ctx = testing.Context(FastAPIDemoCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        leader=True,
    )
    state_out = ctx.run(ctx.on.pebble_ready(container), state_in)
    # Expected plan after Pebble ready with default config
    expected_plan = {
        "services": {
            "fastapi-service": {
                "override": "replace",
                "summary": "fastapi demo",
                "command": "uvicorn api_demo_server.app:app --host=0.0.0.0 --port=8000",
                "startup": "enabled",
                # Since the environment is empty, Layer.to_dict() will not
                # include it.
            }
        }
    }

    # Check that we have the plan we expected:
    assert state_out.get_container(container.name).plan == expected_plan
    # Check the service was started:
    assert container.service_statuses["fastapi-service"] == ops.pebble.ServiceStatus.ACTIVE


def test_config_changed():
    ctx = testing.Context(FastAPIDemoCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        config={"server-port": 8080},
        leader=True,
    )
    ctx.run(ctx.on.config_changed(), state_in)
    assert "--port=8080" in container.layers["fastapi_demo"].services["fastapi-service"].command


def test_config_changed_invalid_port():
    ctx = testing.Context(FastAPIDemoCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        config={"server-port": 22},
        leader=True,
    )
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert state_out.unit_status == testing.BlockedStatus(
        "Invalid port number, 22 is reserved for SSH"
    )


def test_relation_data():
    ctx = testing.Context(FastAPIDemoCharm)
    relation = testing.Relation(
        endpoint="database",
        interface="postgresql_client",
        remote_app_name="postgresql-k8s",
        remote_app_data={
            "endpoints": "example.com:5432",
            "username": "foo",
            "password": "bar",
        },
    )
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        relations={relation},
        leader=True,
    )

    ctx.run(ctx.on.relation_changed(relation), state_in)

    assert container.layers["fastapi_demo"].services["fastapi-service"].environment == {
        "DEMO_SERVER_DB_HOST": "example.com",
        "DEMO_SERVER_DB_PORT": "5432",
        "DEMO_SERVER_DB_USER": "foo",
        "DEMO_SERVER_DB_PASSWORD": "bar",
    }


def test_no_database_blocked():
    ctx = testing.Context(FastAPIDemoCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        leader=True,
    )

    state_out = ctx.run(ctx.on.collect_unit_status(), state_in)

    assert state_out.unit_status == testing.BlockedStatus("Waiting for database relation")
