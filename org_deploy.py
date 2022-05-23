#!/usr/bin/env python3

import boto3
import logging

logger = logging.getLogger(__name__)
loghandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)


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
