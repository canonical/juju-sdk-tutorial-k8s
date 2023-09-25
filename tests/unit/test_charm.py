#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
from charm import FastAPIDemoCharm
from scenario import PeerRelation, Relation, State, Context, Container, Action

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

    @unittest.mock.patch("charm.LogProxyConsumer")
    @unittest.mock.patch("charm.MetricsEndpointProvider")
    @unittest.mock.patch("charm.GrafanaDashboardProvider")
    def test_get_db_info_action(self, *_):
        # use scenario.Context to declare what charm we are testing
        ctx = Context(
            FastAPIDemoCharm,
            meta={
                "name": "demo-api-charm",
                "containers": {"demo-server": {}},
                "peers": {"fastapi-peer": {"interface": "fastapi_demo_peers"}},
                "requires": {
                    "database": {
                        "interface": "postgresql_client",
                    }
                },
            },
            config={
                "options": {
                    "server-port": {
                        "default": 8000,
                    }
                }
            },
            actions={
                "get-db-info": {
                    "params": {"show-password": {"default": False, "type": "boolean"}}
                }
            },
        )

        # declare the input state
        state_in = State(
            leader=True,
            relations=[
                Relation(
                    endpoint="database",
                    interface="postgresql_client",
                    remote_app_name="postgresql-k8s",
                    local_unit_data={},
                    remote_app_data={
                        "endpoints": "127.0.0.1:5432",
                        "username": "foo",
                        "password": "bar",
                    },
                ),
            ],
            containers=[
                Container(name="demo-server", can_connect=True),
            ],
        )

        # ACT: run the action with the defined state and collect the output.
        action = Action("get-db-info", {"show-password": True})
        action_out = ctx.run_action(action, state_in)

        assert action_out.results == {
            "db-host": "127.0.0.1",
            "db-port": "5432",
            "db-username": "foo",
            "db-password": "bar",
        }
