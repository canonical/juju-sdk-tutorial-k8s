#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
from charm import FastAPIDemoCharm

import ops
import ops.testing
import unittest
import unittest.mock


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = ops.testing.Harness(FastAPIDemoCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @unittest.mock.patch(
        "charm.FastAPIDemoCharm.version", new_callable=unittest.mock.PropertyMock
    )
    @unittest.mock.patch("charm.FastAPIDemoCharm.fetch_postgres_relation_data")
    def test_pebble_layer(self, mock_fetch_postgres_relation_data, mock_version):
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
                        "DEMO_SERVER_DB_PORT": None,
                        "DEMO_SERVER_DB_USER": None,
                    },
                }
            }
        }
        mock_fetch_postgres_relation_data.return_value = {}
        mock_version.return_value = "1.0.0"

        # Simulate the container coming up and emission of pebble-ready event
        self.harness.container_pebble_ready("demo-server")
        # Get the plan now we've run PebbleReady
        updated_plan = self.harness.get_container_pebble_plan("demo-server").to_dict()
        # Check we've got the plan we expected
        self.assertEqual(expected_plan, updated_plan)
        # Check the service was started
        service = self.harness.model.unit.get_container("demo-server").get_service(
            "fastapi-service"
        )
        self.assertTrue(service.is_running())
        # Ensure we set an ActiveStatus with no message
        self.assertEqual(self.harness.model.unit.status, ops.ActiveStatus())

        # Check port configuration for SSH (port 22) and assert BlockedStatus
        self._assert_port_configuration(22, ops.BlockedStatus('Invalid port number, 22 is reserved for SSH'))
        # Check port configuration for a custom port (e.g., 1234) and assert ActiveStatus 
        self._assert_port_configuration(1234, ops.ActiveStatus())

    def _assert_port_configuration(self, port_number, expected_status):

        # Update the server-port configuration with the specified port number
        self.harness.update_config({"server-port": port_number})

        # Get the set of opened ports from the juju unit
        currently_opened_ports = self.harness.model.unit.opened_ports()

        # Extract the port numbers from the opened ports set
        port_numbers = {port.port for port in currently_opened_ports}

        # Retrieve the updated server port configuration from the charm config
        server_port_config = self.harness.model.config.get("server-port")

        # Check if the server port is 22 (reserved for SSH)
        if port_number == 22:
            # Assert that the SSH port is not in the set of opened ports
            self.assertNotIn(server_port_config, port_numbers)
        else:
            # Assert that the specified port is in the set of opened ports
            self.assertIn(server_port_config, port_numbers)

        # Assert that the unit status matches the expected status
        self.assertEqual(self.harness.model.unit.status, expected_status)