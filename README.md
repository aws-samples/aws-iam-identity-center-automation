# AWS IAM Identity Center Configuration Automation

This project accelerates the implementation of # AWS IAM Identity Center by automating the configuration of permission sets and assignments using AWS Cloud Development Kit (CDK).

## Prerequisites

Before you start you should have the following prerequisites:

- An Organization in [AWS Organizations](https://docs.aws.amazon.com/organizations/index.html)
- [Groups](https://docs.aws.amazon.com/singlesignon/latest/userguide/users-groups-provisioning.html#groups-concept) in [AWS IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html)
- Administrative access for the Organization Management account
- Python version 3.7.10 or later
- Git
- [AWS CDK v2](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

## Environment Set up

Clone this repo:
```shell
$ git clone https://github.com/aws-samples/aws-iam-identity-center-automation.git
```

 To create a virtualenv run the following command after installing python:
```shell
python3 -m venv .env
```

On ***macOS/Linux*** run the following command to activate your virtualenv:
```shell
source .env/bin/activate
````

On ***Windows*** run the following command to activate the virtualenv:
```shell
.env\Scripts\activate.bat
````

Once the virtualenv is activated, install the required dependencies:
```shell
pip install -r requirements.txt
```

We recommend setting up a [named profile for the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html) using the administrative credentials for the Organization Management account to use when running commands. You can also [configure your AWS profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) using the following command, which will set up the default profile:
```shell
aws configure
```

## Test
Try to view the Help (-h) command to make sure that you have your environment setup correctly:

```shell
python sso_automation.py sso -h
```

You can use the following command to output a JSON file named "org_data.json", that describes your AWS Organization structure with the 
necessary IDs to use in the AWS IAM Identity Center input files:
```shell
python sso_automation.py describe-org --profile SSO-test
```

## Bootstrap AWS Environment

Generate and deploy the CDK Bootstrap CloudFormation template manually.

***macOS/Linux:***
```shell
cdk bootstrap --show-template > ./cfn_templates/bootstrap-template.yaml
```

***Windows:***
```shell
powershell "cdk bootstrap --show-template | Out-File -encoding utf8 ./cfn_templates/bootstrap-template.yaml"
```

Once you have the CDK Bootstrap template generated login to the [AWS Console](https://console.aws.amazon.com/) and deploy it using CloudFormation.

This prepares the environment so that you can deploy your changes directly using CDK. Please note, we always recommend 
a thorough review before deploying though. 

## AWS IAM Identity Center Automation

### Custom Policies
Create all your inline custom IAM policies inside the sub folder [inline_policies](/inline_policies/), there are a few examples there already.

### Define Permission Sets
Create a file named “permsets.json” in the root folder and put in the details for the permission sets you would like to create. 
You can use the [example_permsets.json](example_permsets.json) file included in the root folder to get started.

### Define Assignments
Next, create a text file named “assignments.json” in the root folder and put in the details
for the new account assignments you would like to create. Use the target to change the
scope with the option to apply to all accounts, all accounts under an OU or one specific
account. You can use the [example_assignments.json](example_assignments.json) file included in the root folder to get started.

### Generate, Deploy and Destroy

The following command will generate the cloudformation to apply the configured changes without deploying them 
```shell
python sso_automation.py sso --region us-east-1 --profile SSO-test --mgmtacct 123456789012 --permsets permsets.json --assignments assignments.json
```

Deploy the stack by adding the "--deploy" flag
```shell
python sso_automation.py sso --region us-east-1 --profile SSO-test --mgmtacct 123456789012 --permsets permsets.json --assignments assignments.json --deploy
```

Destroy the stack by adding the "--destroy" flag
```shell
python sso_automation.py sso --region us-east-1 --profile SSO-test --mgmtacct 123456789012 --permsets permsets.json --assignments assignments.json --destroy
```

### Troubleshooting

#### Error: The CreateStackSet operation fails.
An error occurred (ValidationError) when calling the CreateStackSet operation: You must enable organizations access to operate a service managed stack set

#### Resolution: Enable Trusted Access.

Follow these instructions to [Enable Trusted Access](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html):
https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
