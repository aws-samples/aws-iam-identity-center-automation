# AWS SSO Configuration Automation

This project accelerates the implementation of AWS SSO by automating the configuration of permission sets and assignments using AWS CDK.

## Environment Set up
 To manually create a virtualenv run the following command after installing python:
```shell
python3 -m venv .env
```

On ***macOS/Linux*** you can run the following command to activate your virtualenv:
```shell
source .env/bin/activate
````

On ***Windows*** you can run the following command to activate the virtualenv:
```shell
.env\Scripts\activate.bat
````

Once the virtualenv is activated, you can install the required dependencies.
```shell
pip install -r requirements.txt
```

Configure your AWS profile using the administrative credentials to the Organization Management account
```shell
aws configure
```

## Test
Try to view the Help (-h) of our program to make sure that you have your environment setup correctly:

```shell
python sso_automation.py sso -h
```

You can use the following command to output a JSON file named "org_data.json", that describes your AWS Organization structure with the 
necessary ID's to use in the AWS SSO input files
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

## SSO Automation

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
