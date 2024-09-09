#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
import ops
import ops.testing
import pytest

from charm import FastAPIDemoCharm


@pytest.fixture
def harness():
    harness = ops.testing.Harness(FastAPIDemoCharm)
    harness.begin()
    yield harness
    harness.cleanup()


def test_pebble_layer(
    monkeypatch: pytest.MonkeyPatch, harness: ops.testing.Harness[FastAPIDemoCharm]
):
    monkeypatch.setattr(FastAPIDemoCharm, "version", "1.0.0")
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

    # Simulate the container coming up and emission of pebble-ready event
    harness.container_pebble_ready("demo-server")
    harness.evaluate_status()

    # Get the plan now we've run PebbleReady
    updated_plan = harness.get_container_pebble_plan("demo-server").to_dict()
    service = harness.model.unit.get_container("demo-server").get_service("fastapi-service")
    # Check that we have the plan we expected:
    assert updated_plan == expected_plan
    # Check the service was started:
    assert service.is_running()
    # Ensure we set a BlockedStatus with appropriate message:
    assert isinstance(harness.model.unit.status, ops.BlockedStatus)
    assert "Waiting for database" in harness.model.unit.status.message


@pytest.mark.parametrize(
    "port,expected_status",
    [
        (22, ops.BlockedStatus("Invalid port number, 22 is reserved for SSH")),
        (1234, ops.BlockedStatus("Waiting for database relation")),
    ],
)
def test_port_configuration(
    monkeypatch, harness: ops.testing.Harness[FastAPIDemoCharm], port, expected_status
):
    # Given
    monkeypatch.setattr(FastAPIDemoCharm, "version", "1.0.1")
    harness.container_pebble_ready("demo-server")
    # When
    harness.update_config({"server-port": port})
    harness.evaluate_status()
    currently_opened_ports = harness.model.unit.opened_ports()
    port_numbers = {port.port for port in currently_opened_ports}
    server_port_config = harness.model.config.get("server-port")
    unit_status = harness.model.unit.status
    # Then
    if port == 22:
        assert server_port_config not in port_numbers
    else:
        assert server_port_config in port_numbers
    assert unit_status == expected_status
