import boto3
from aws_cdk import Environment, Stack
from aws_cdk import aws_sso as sso
from constructs import Construct
import json
import logging
import re
import org_enum

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

pattern_email = r'^[a-zA-Z0-9]+(([\.]|[-]|[_]|[+])(?![\.-_])\w+)?[@][^-][a-zA-Z0-9-]+[^-](\.[a-zA-Z]{2,4}){1,3}$'
pattern_account = r'123456789|(\d)\1{11,11}'
pattern_account_id = r'^(\d){12}$'


def check_email(email):
    flag = False
    if re.search(pattern_email, email):
        flag = True
    return bool(flag)


def check_acct(acct):
    flag = False
    if re.search(pattern_account_id, acct):
        if re.search(pattern_account, acct):
            return bool(flag)
        else:
            flag = True
            return bool(flag)


def get_permission_sets(permission_sets):
    managed_policy_list = []
    permission_set_name = []
    custom_policy_list = []
    with open(permission_sets, "r") as perm_file:
        for permset in perm_file:
            perm_name = permset.split(",")[0]
            permission_set_name.append(perm_name)
            managed_policies = permset.strip().split(",")[1]
            if "|" in managed_policies:
                managed_policy_list.append(managed_policies.strip().split("|"))
            else:
                managed_policy_list.append(managed_policies)
            custom_policy = permset.strip().split(",")[2]
            custom_policy_list.append(custom_policy)
    return permission_set_name, managed_policy_list, custom_policy_list


def list_sso_instances(sso_session):
    paginator = sso_session.get_paginator('list_instances')
    page_iterator = paginator.paginate()
    for page in page_iterator:
        for instance in page['Instances']:
            # Note: assume one SSO instance only
            instance_arn = instance["InstanceArn"]
            id_store = instance["IdentityStoreId"]
    return instance_arn, id_store


def get_group_ids(profile, id_store, group_name):
    session = boto3.Session(profile_name=profile)
    id_store_client = session.client("identitystore")
    group_details = {}
    groups = id_store_client.list_groups(IdentityStoreId=id_store,
                                         Filters=[{'AttributePath': 'DisplayName', 'AttributeValue': group_name}])
    for response in groups['Groups']:
        group_details[group_name] = response['GroupId']

    return group_details


def get_target_account(profile, target):
    org_accounts = []
    o = re.match(r'^ou-', target)
    m = re.fullmatch(r'All', target, flags=re.I)
    a = re.match(r'[0-9]', target)
    if m:
        org_accounts = org_enum.get_all_accounts(profile)
    if a:
        org_accounts.append(target)
    if o:
        org_accounts = org_enum.get_accounts_for_ou(profile, target)
    return org_accounts


def get_assign(assignments, profile, sso_id_store):
    allocated = []
    with open(assignments, "r") as assign_file:
        for assign in assign_file:
            assign = assign.strip()
            if assign == "":
                continue
            else:
                logger.debug("assign: " + assign)

                perm_set = assign.split(",")[0]
                grp_name = assign.split(",")[1]
                group_details = get_group_ids(profile, sso_id_store, grp_name)
                target = assign.split(",")[2].strip()
                target_accounts = get_target_account(profile, target)
                allocated.append((group_details, target_accounts, perm_set))
    return allocated


class AWSSSOStack(Stack):

    def __init__(self, scope: Construct, id: str, ssopermsets: str, ssoassigns: str, profile: str,
                 env: Environment, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.permnames, self.managedpolicies, self.custompolicies = get_permission_sets(ssopermsets)
        self.session = boto3.Session(profile_name=profile)
        self.sso_session = self.session.client('sso-admin', region_name=env.region)
        self.ssoinstancearn, self.ssoidstore = list_sso_instances(self.sso_session)

        perm_sets = {}
        index = 0
        for perm_name in self.permnames:
            if self.custompolicies[index]:
                with open('./inline_policies/' + self.custompolicies[index], 'r') as f:
                    check = f.read()
                    try:
                        custom_policy_contents = json.loads(check)
                    except ValueError as e:
                        logger.debug(
                            f"Inline Policy {self.custompolicies[index]} is not in a valid JSON format. Error {e}")
                if isinstance(self.managedpolicies[index], list):
                    if self.managedpolicies[index] == "":
                        self.permset = sso.CfnPermissionSet(
                            self, perm_name,
                            instance_arn=self.ssoinstancearn,
                            name=perm_name,
                            inline_policy=custom_policy_contents
                        )
                    else:
                        self.permset = sso.CfnPermissionSet(
                            self, perm_name,
                            instance_arn=self.ssoinstancearn,
                            name=perm_name,
                            managed_policies=self.managedpolicies[index],
                            inline_policy=custom_policy_contents
                        )
                else:
                    if self.managedpolicies[index] == "":
                        self.permset = sso.CfnPermissionSet(
                            self, perm_name,
                            instance_arn=self.ssoinstancearn,
                            name=perm_name,
                            inline_policy=custom_policy_contents
                        )
                    else:
                        self.permset = sso.CfnPermissionSet(
                            self, perm_name,
                            instance_arn=self.ssoinstancearn,
                            name=perm_name,
                            managed_policies=[self.managedpolicies[index]],
                            inline_policy=custom_policy_contents
                        )
            else:
                if isinstance(self.managedpolicies[index], list) and self.managedpolicies[index] != "":
                    self.permset = sso.CfnPermissionSet(
                        self, perm_name,
                        instance_arn=self.ssoinstancearn,
                        name=perm_name,
                        managed_policies=self.managedpolicies[index]
                    )
                else:
                    self.permset = sso.CfnPermissionSet(
                        self, perm_name,
                        instance_arn=self.ssoinstancearn,
                        name=perm_name,
                        managed_policies=[self.managedpolicies[index]]
                    )
            perm_sets[perm_name] = self.permset.attr_permission_set_arn
            index += 1
        # Get default permission sets
        try:
            list_paginator = self.sso_session.get_paginator('list_permission_sets')
            for response in list_paginator.paginate(InstanceArn=self.ssoinstancearn):
                for ps in response['PermissionSets']:
                    details = self.sso_session.describe_permission_set(
                        InstanceArn=self.ssoinstancearn,
                        PermissionSetArn=ps
                    )
                    ps_name = details['PermissionSet']['Name']
                    # if ps_name.startswith('AWS'):
                    perm_sets[ps_name] = details['PermissionSet']['PermissionSetArn']
        except Exception as e:
            print(e)

        self.permission_set_arns = perm_sets
        self.allocated = get_assign(ssoassigns, profile, self.ssoidstore)
        logger.debug(f"{self.allocated}")
        count = 1
        for item in self.allocated:
            logger.debug(f"item: {item}")

            # if item[0] is empty it's likely an invalid sso group name
            if len(item[0]) <= 0:
                logger.warning("Please check the SSO group names in your assignments file")

            for acct_id in item[1]:
                logger.debug(f"acct_id: {acct_id}")
                for k in item[0].keys():
                    grp_name = k
                for v in item[0].values():
                    principal_id = v

                self.assign = sso.CfnAssignment(
                    self, grp_name + "Assignment" + str(count),
                    instance_arn=self.ssoinstancearn,
                    permission_set_arn=self.permission_set_arns[item[2]],
                    principal_id=principal_id,
                    principal_type="GROUP",
                    target_id=acct_id,
                    target_type="AWS_ACCOUNT"
                )
                count += 1
