#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk
from unittest.mock import Mock

import scenario

from charm import FastAPIDemoCharm


def test_get_db_info_action(monkeypatch):

    monkeypatch.setattr("charm.LogProxyConsumer", Mock())
    monkeypatch.setattr("charm.MetricsEndpointProvider", Mock())
    monkeypatch.setattr("charm.GrafanaDashboardProvider", Mock())

    # Use scenario.Context to declare what charm we are testing.
    ctx = scenario.Context(
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
            "get-db-info": {"params": {"show-password": {"default": False, "type": "boolean"}}}
        },
    )

    # Declare the input state.
    state_in = scenario.State(
        leader=True,
        relations=[
            scenario.Relation(
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
            scenario.Container(name="demo-server", can_connect=True),
        ],
    )

    # run the action with the defined state and collect the output.
    action = scenario.Action("get-db-info", {"show-password": True})
    action_out = ctx.run_action(action, state_in)

    assert action_out.results == {
        "db-host": "127.0.0.1",
        "db-port": "5432",
        "db-username": "foo",
        "db-password": "bar",
    }
