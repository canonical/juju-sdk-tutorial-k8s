#!/usr/bin/env python3
# Copyright 2023 benjamin
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

from helpers import is_port_open, get_address

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = METADATA["name"]


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # Build and deploy charm from local source folder
    charm = await ops_test.build_charm(".")
    resources = {
        "demo-server-image": METADATA["resources"]["demo-server-image"][
            "upstream-source"
        ]
    }

    # Deploy the charm and wait for waiting/idle status
    # The app will not be in active status as this requires a database relation
    await asyncio.gather(
        ops_test.model.deploy(charm, resources=resources, application_name=APP_NAME),
        ops_test.model.wait_for_idle(
            apps=[APP_NAME], status="waiting", raise_on_blocked=True, timeout=1000
        ),
    )


@pytest.mark.abort_on_fail
async def test_database_integration(ops_test: OpsTest):
    """Verify that the charm integrates with the database.

    Assert that the charm is active if the integration is established.
    """
    await ops_test.model.deploy(
        application_name="postgresql-k8s",
        entity_url="https://charmhub.io/postgresql-k8s",
        channel="14/stable",
    )
    await ops_test.model.integrate(f"{APP_NAME}", "postgresql-k8s")
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=1000
    )

@pytest.mark.abort_on_fail
async def test_open_ports(ops_test: OpsTest):
    """Verify that setting the server-port in charm's config correctly adjust k8s service

    Assert blocked status in case of port 22 and active status for others
    """
    app = ops_test.model.applications.get("demo-api-charm")

    # Get the k8s service address of the app
    address = await get_address(ops_test=ops_test, app_name=APP_NAME)
    # Validate that initial port is opened
    assert is_port_open(address, 8000)

    # Set Port to 22 and validate app going to blocked status with port not opened
    await app.set_config({"server-port": "22"})
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="blocked", timeout=1000
    ),
    assert not is_port_open(address, 22)

    # Set Port to 6789 "Dummy port" and validate app going to active status with port opened
    await app.set_config({"server-port": "6789"})
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", timeout=1000
    ),
    assert is_port_open(address, 6789)