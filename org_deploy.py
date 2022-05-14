#!/usr/bin/env python3

import boto3
import sys
import logging
import time
from typing import List

logger = logging.getLogger(__name__)
loghandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)

FAILURE_TOLERANCE_COUNT = 0
MAX_CONCURRENT_COUNT = 10

DEFAULT_RETRIES = 50
DEFAULT_WAIT = 10


class Parameter:
    def __init__(self, parameter_name: str, parameter_value: str):
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value

    def to_json(self):
        res = {
            "ParameterKey": self.parameter_name,
            "ParameterValue": self.parameter_value,
        }
        return res


def parse_parameters(parameters):
    parameter_list = []
    parameter_results = []
    for param in parameters:
        parameter_list.append(Parameter(parameter_name=param["ParameterKey"], parameter_value=param["DefaultValue"]))
    for param in parameter_list:
        param_item = param.to_json()
        parameter_results.append(param_item)
    return parameter_results


def parse_yaml_template(yaml_template, profile, region):
    session = boto3.Session(profile_name=profile)
    cfn_session = session.client("cloudformation", region_name=region)
    with open(yaml_template, "r") as template:
        template_body = "".join(template.readlines())
        template_info = cfn_session.get_template_summary(TemplateBody=template_body)
        parameter_list = parse_parameters(template_info['Parameters'])
    template.close()
    return template_body, parameter_list


def get_accounts_for_ou(profile, ou):
    accounts = []
    session = boto3.Session(profile_name=profile)
    org_session = session.client("organizations", region_name="us-east-1")
    paginator = org_session.get_paginator('list_organizational_units_for_parent')
    for response in paginator.paginate(ParentId=ou):
        sub_ous = [data['Id'] for data in response['OrganizationalUnits']]
        for sub_ou_id in sub_ous:
            accounts.extend(get_accounts_for_ou(profile, sub_ou_id))
    paginator = org_session.get_paginator('list_accounts_for_parent')
    for response in paginator.paginate(ParentId=ou):
        accounts.extend(data['Id'] for data in response['Accounts'])

    return accounts


def list_org_ous(profile):
    session = boto3.Session(profile_name=profile)
    org_session = session.client("organizations", region_name="us-east-1")
    paginator = org_session.get_paginator('list_roots')
    page_iterator = paginator.paginate()
    root_id = ""
    for page in page_iterator:
        for rt in page['Roots']:
            root_id = rt['Id']
    logger.debug(f"Getting OUs directly under Root {root_id}")
    paginator2 = org_session.get_paginator('list_organizational_units_for_parent')
    page_iterator2 = paginator2.paginate(ParentId=root_id)
    ou_ids = []
    for page in page_iterator2:
        ou_ids.extend(ou['Id'] for ou in page['OrganizationalUnits'])
    for top_parent_id in ou_ids:
        paginator = org_session.get_paginator('list_children')
        page_iterator = paginator.paginate(ParentId=top_parent_id, ChildType='ORGANIZATIONAL_UNIT')
        for page in page_iterator:
            ou_ids.extend(childou['Id'] for childou in page['Children'])
    return ou_ids


def get_all_accounts(profile):
    session = boto3.Session(profile_name=profile)
    org_session = session.client("organizations", region_name="us-east-1")
    paginator = org_session.get_paginator('list_accounts')
    page_iterator = paginator.paginate()
    accounts = []
    for page in page_iterator:
        for acct in page['Accounts']:
            if acct['Status'] == "ACTIVE":
                accounts.append(acct['Id'])
    return accounts


def check_trusted_access(profile):
    session = boto3.Session(profile_name=profile)
    org_session = session.client("organizations", region_name="us-east-1")
    resp = org_session.list_aws_service_access_for_organization()
    service_principals = resp['EnabledServicePrincipals']
    flag = True
    for serv_princ in service_principals:
        if serv_princ['ServicePrincipal'] == 'member.org.stacksets.cloudformation.amazonaws.com':
            flag = False
            logger.debug(f"Stacksets trust access is already enabled")
            pass
    if flag:
        org_session.enable_aws_service_access(ServicePrincipal='member.org.stacksets.cloudformation.amazonaws.com')
        logger.debug(f"Stacksets trust access was found disabled and now enabled")
    return flag


def copy_cfn_to_s3(cfn_file, bucket_name, profile, region):
    session = boto3.Session(profile_name=profile)
    s3_client = session.client('s3', region_name=region)

    try:
        fh = open(cfn_file, "r")
        contents = fh.read()
    except:
        logger.debug(f"Cannot open CFN template {cfn_file}")
        sys.exit()
    obj_key = cfn_file.split("/")[2]
    response = s3_client.put_object(
        ACL='bucket-owner-full-control',
        Body=contents,
        Bucket=bucket_name,
        ContentType='application/json',
        Key=obj_key,
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.debug(f"File {cfn_file} uploaded to S3 bucket successfully!")
    else:
        logger.debug(f"Error: {response['ResponseMetadata']}")


class StackSet:
    def __init__(self, name: str, profile: str, region: str, deploy_target: List, template: str, template_url: str,
                 parameters: List):
        self.name = name
        self.profile = profile
        self.region = region
        self.deploytarget = deploy_target
        self.template = template
        self.templateurl = template_url
        self.parameters = parameters
        self.session = boto3.Session(profile_name=profile)
        self.cfn_client = self.session.client('cloudformation')

    def create_stackset(self, desc: str):
        resp = self.cfn_client.create_stack_set(
            StackSetName=self.name,
            Description=desc,
            TemplateBody=self.template,
            Parameters=self.parameters,
            Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            PermissionModel="SERVICE_MANAGED",
            AutoDeployment={"Enabled": True, "RetainStacksOnAccountRemoval": False},
            ClientRequestToken=self.name,
        )
        stackset_id = self.wait_for_me()
        if stackset_id:
            logger.debug(f"StacksetId {stackset_id} is created.")
        return resp

    def create_stackset_instances(self):
        resp = self.cfn_client.create_stack_instances(
            StackSetName=self.name,
            DeploymentTargets={"OrganizationalUnitIds": self.deploytarget},
            Regions=[self.region],
            ParameterOverrides=self.parameters,
            OperationPreferences={
                "RegionOrder": [self.region],
                "FailureToleranceCount": FAILURE_TOLERANCE_COUNT,
                "MaxConcurrentCount": MAX_CONCURRENT_COUNT,
            },
        )
        op_id = resp["OperationId"]
        self.wait_for_my_operation(op_id)
        return resp

    def delete_stackset_instance(self):
        resp = self.cfn_client.delete_stack_instances(
            StackSetName=self.name,
            DeploymentTargets={'OrganizationalUnitIds': self.deploytarget},
            Regions=[self.region],
            OperationPreferences={
                "RegionOrder": [self.region],
                "FailureToleranceCount": FAILURE_TOLERANCE_COUNT,
                "MaxConcurrentCount": MAX_CONCURRENT_COUNT,
            },
            RetainStacks=False
        )
        op_id = resp["OperationId"]
        self.wait_for_my_operation(op_id)
        return resp

    def delete_stackset(self):
        resp = self.cfn_client.delete_stack_set(
            StackSetName=self.name
        )
        return resp

    def wait_for_me(self, delay=DEFAULT_WAIT, max_retries=DEFAULT_RETRIES):
        for i in range(1, max_retries):
            resp = self.get_stack_set_detail()
            if resp is None:
                logger.debug(f"Stack {self.name} does not exist")
            else:
                resp = resp["StackSet"]
                status = resp["Status"]
                if status != "ACTIVE":
                    logger.debug(f"Waiting for {resp['StackSetId']} status {status} count {i}/{max_retries}")
                else:
                    logger.debug(f"Finished waiting for {resp['StackSetId']} status {status} count {i}/{max_retries}")
                    return resp["StackSetId"]
            time.sleep(delay)

    def get_stack_set_detail(self):
        try:
            resp = self.cfn_client.describe_stack_set(StackSetName=self.name)
            return resp
        except Exception as error:
            logger.debug(f"Could not get StackSet {self.name} {error}")
            return None

    def wait_for_my_operation(self, op_id: str, delay=DEFAULT_WAIT, max_retries=DEFAULT_RETRIES):
        for i in range(1, max_retries):
            resp = self.get_stack_set_operation_detail(op_id)
            if resp is None:
                logger.debug(f"Stack {self.name} {op_id} does not exist")
            else:
                resp = resp["StackSetOperation"]
                status = resp["Status"]
                if status == "RUNNING":
                    logger.debug(f"Waiting for {resp['StackSetId']} status {status} count {i}/{max_retries}")
                else:
                    logger.debug(f"Operation returned {resp['StackSetId']} status {status} count {i}/{max_retries}")
                    if status == "FAILED":
                        logger.debug(resp)
                    return resp["OperationId"]
            time.sleep(delay)

    def get_stack_set_operation_detail(self, opid: str):
        try:
            resp = self.cfn_client.describe_stack_set_operation(
                StackSetName=self.name,
                OperationId=opid
            )
            return resp
        except Exception as error:
            logger.debug(f"Could not get StackSet operations {self.name} {opid} {error}")
            return None
