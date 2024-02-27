#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
from charm import FastAPIDemoCharm

import ops
import ops.testing
import pytest


@pytest.fixture
def harness():
    harness = ops.testing.Harness(FastAPIDemoCharm)
    harness.begin()
    yield harness
    harness.cleanup()


@pytest.fixture(autouse=True)
def _patched_postgres_relation_data(monkeypatch):
    def mock_return(*_):
        return {}

    monkeypatch.setattr(FastAPIDemoCharm, "fetch_postgres_relation_data", mock_return)


@pytest.fixture(autouse=True)
def _patched_version(monkeypatch):
    monkeypatch.setattr(FastAPIDemoCharm, "version", "1.0.0")


def test_pebble_layer(harness: ops.testing.Harness[FastAPIDemoCharm]):
    # Expected plan after Pebble ready with default config
    expected_plan = {
        "services": {
            "fastapi-service": {
                "override": "replace",
                "summary": "fastapi demo",
                "command": "uvicorn api_demo_server.app:app --host=0.0.0.0 --port=8000",
                "startup": "enabled",
                "environment": {
                    "DEMO_SERVER_DB_HOST": None,
                    "DEMO_SERVER_DB_PASSWORD": None,
                    "DEMO_SERVER_DB_USER": None,
                    "DEMO_SERVER_DB_PORT": None,
                },
            }
        }
    }

    # Simulate the container coming up and emission of pebble-ready event
    harness.container_pebble_ready("demo-server")
    # Get the plan now we've run PebbleReady
    updated_plan = harness.get_container_pebble_plan("demo-server").to_dict()
    service = harness.model.unit.get_container("demo-server").get_service(
        "fastapi-service"
    )
    status = harness.model.unit.status

    # Check that we have the plan we expected
    assert updated_plan == expected_plan
    # Check the service was started
    assert service.is_running()
    # Ensure we set an ActiveStatus with no message
    assert status == ops.ActiveStatus()
