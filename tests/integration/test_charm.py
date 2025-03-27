#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # Build and deploy charm from local source folder
    charm = await ops_test.build_charm(".")
    resources = {
        "demo-server-image": METADATA["resources"]["demo-server-image"]["upstream-source"]
    }

    # Deploy the charm and wait for blocked/idle status
    # The app will not be in active status as this requires a database relation
    await asyncio.gather(
        ops_test.model.deploy(charm, resources=resources, application_name=APP_NAME),
        ops_test.model.wait_for_idle(
            apps=[APP_NAME], status="blocked", raise_on_blocked=False, timeout=120
        ),
    )


@pytest.mark.abort_on_fail
async def test_database_integration(ops_test: OpsTest):
    """Verify that the charm integrates with the database.

    Assert that the charm is active if the integration is established.
    """
    await ops_test.model.deploy(
        application_name="postgresql-k8s",
        entity_url="postgresql-k8s",
        channel="14/stable",
    )
    await ops_test.model.integrate(f"{APP_NAME}", "postgresql-k8s")
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", raise_on_blocked=False, timeout=120
    )
