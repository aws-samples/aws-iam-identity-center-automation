#!/usr/bin/env python3

from aws_cdk import App, Environment
from sso_automation_app.sso_stack import AWSSSOStack
import logging

logger = logging.getLogger(__name__)
loghandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)

app = App()
profile = app.node.try_get_context("profile")
account_id = app.node.try_get_context("accountID")
region_name = app.node.try_get_context("region")
stage = app.node.try_get_context("stage")
stage_bucket = app.node.try_get_context("stagebucket")
organization_id = app.node.try_get_context("orgid")
sso_permission_sets = app.node.try_get_context("permsets")
sso_assignments = app.node.try_get_context("assignments")

env_info = Environment(account=account_id, region=region_name)

if profile and env_info:
    if sso_permission_sets and sso_assignments:
        AWSSSOStack(app, "awssso-stack", sso_permission_sets, sso_assignments, profile, env=env_info)
else:
    logger.debug("Failed to specify a profile and environment")

app.synth()
