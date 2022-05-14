#!/usr/bin/env python3

import argparse
import json
import subprocess
import logging
import os
import boto3

logger = logging.getLogger(__name__)
loghandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)
logger.setLevel(logging.DEBUG)


def build_parser():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--version", action="version", version=f'%(prog)s 1.0.0')
    subparsers = arg_parser.add_subparsers(dest='subcommand', help="sub-command help")
    sso_parser = subparsers.add_parser('sso', help='AWS SSO stack')
    sso_parser.add_argument("--permsets", dest="permsets", help="File containing permission sets")
    sso_parser.add_argument("--assignments", dest="assignments", help="File containing assignments")
    sso_parser.add_argument("--mgmtacct", help="AWS Organizations Management Account")
    sso_parser.add_argument("-p", "--profile", dest="profile", required=True, help="Your AWS profile")
    sso_parser.add_argument("-r", "--region", dest="region", required=True, help="AWS Region")
    sso_parser.add_argument("-d", "--deploy", action="store_true", default=False, required=False, help="Deploy changes")
    sso_parser.add_argument("--destroy", action="store_true", default=False, required=False, help="Destroy the deployed CFN stack")

    org_parser = subparsers.add_parser('describe-org', help='Describe entire AWS Organization')
    org_parser.add_argument("-p", "--profile", dest="profile", required=True, help="Your AWS profile")

    return arg_parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if args.profile:
        session = boto3.Session(profile_name=args.profile)

    if args.subcommand == "describe-org":
        org_client = session.client('organizations')

        aws_organization = {}
        org_response = org_client.describe_organization()
        aws_organization['Organization'] = org_response['Organization']

        root_response = org_client.list_roots()
        aws_organization['Roots'] = root_response['Roots']

        root_count = -1
        for root_ou in root_response['Roots']:
            root_count += 1

            org_id = root_ou['Id']
            aws_organization['Roots'][root_count]['Children'] = []
            ou_response = org_client.list_children(ParentId=org_id, ChildType='ORGANIZATIONAL_UNIT')

            for child_ou in ou_response['Children']:
                ou_unit_id = child_ou['Id']
                ou_details = org_client.describe_organizational_unit(OrganizationalUnitId=ou_unit_id)
                aws_organization['Roots'][root_count]['Children'].append(ou_details['OrganizationalUnit'])
        logger.debug(aws_organization)
        json_string = json.dumps(aws_organization, indent=4)
        org_info_file = 'org_data.json'

        # Write out Org Structure using a JSON string
        with open(org_info_file, 'w') as outfile:
            outfile.write(json_string)

        logger.info(f"AWS Organization info saved in {org_info_file}")

    if args.subcommand == "sso":
        output_dir = "./cfn_templates/"
        output_file = "aws_sso_auto.json"
        sso_stack = output_dir + output_file

        if args.permsets and args.assignments and args.destroy is False:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            synth_cmd = "cdk synth -j --ec2creds false -c permsets=" + args.permsets + " -c assignments=" + \
                        args.assignments + " -c accountID=" + args.mgmtacct + " -c region=" + args.region + \
                        " -c profile=" + args.profile + " --profile " + args.profile + " > " + sso_stack

            sso_response = subprocess.run(synth_cmd, shell=True)

            if sso_response.returncode == 0:
                logger.info(f"Template generated in {sso_stack}")
            else:
                logger.info(f"Failed to synth template for AWS SSO permission sets")

            if args.deploy:
                sso_deploy_cmd = "cdk deploy --ec2creds false -c permsets=" + args.permsets + " -c assignments=" + \
                                 args.assignments + " -c accountID=" + args.mgmtacct + " -c region=" + args.region + \
                                 " -c profile=" + args.profile + " --profile " + args.profile
                sso_deploy_resp = subprocess.run(sso_deploy_cmd, shell=True)

        if args.permsets and args.assignments and args.destroy:
            cmd = "cdk destroy --ec2creds false -c permsets=" + args.permsets + " -c assignments=" + args.assignments \
                  + " -c accountID=" + args.mgmtacct + " -c region=" + args.region + " -c profile=" + args.profile \
                  + " --profile " + args.profile
            sso_response = subprocess.run(cmd, shell=True)
