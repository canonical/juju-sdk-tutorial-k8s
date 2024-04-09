#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
from charm import FastAPIDemoCharm
from scenario import Relation, State, Context, Container, Action, PeerRelation

import unittest
import unittest.mock


class TestCharm(unittest.TestCase):
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

        #run the action with the defined state and collect the output.
        action = Action("get-db-info", {"show-password": True})
        action_out = ctx.run_action(action, state_in)

        assert action_out.results == {
            "db-host": "127.0.0.1",
            "db-port": "5432",
            "db-username": "foo",
            "db-password": "bar",
        }

    @unittest.mock.patch("charm.LogProxyConsumer")
    @unittest.mock.patch("charm.MetricsEndpointProvider")
    @unittest.mock.patch("charm.GrafanaDashboardProvider")
    def test_open_port(self, *_):
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
                PeerRelation(
                    endpoint="fastapi-peer",
                    peers_data={"unit_stats": {"started_counter": "0"}},
                )
            ],
            containers=[
                Container(name="demo-server", can_connect=True),
            ],
        )

        state1 = ctx.run("config_changed", state_in)

        assert len(state1.opened_ports) == 1
        assert state1.opened_ports[0].port == 8000
        assert state1.opened_ports[0].protocol == "tcp"
