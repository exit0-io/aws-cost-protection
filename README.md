# AWS Learning Budget Keeper

New AWS users often make simple mistakes that can accidentally lead to high bills — like forgetting to shut down an EC2 instance or choosing an expensive disk.
To help you avoid that, we provide a ready-made automation that protects your account from these common issues.

This automation is based on an service called [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html), and includes:

- ✅ Modifies your IAM group to restrict from launching large or expensive instance types and volumes.
- ✅ Automatic shutdown of EC2 instances multiple times a day (you'll decide when), to avoid idle costs.
- ✅ Auto Scaling Groups (ASG) set to zero multiple times a day.

This automation is deployed using a **CloudFormation template** — an AWS tool that sets everything up for you, safely and automatically.

> [!NOTE]
> This is **not a full protection system for your AWS account**.
> It only covers common services and usage patterns relevant to this course.

> [!WARNING]
> This automation will **affect all resources in the selected regions in your AWS account** — including ones you may have created before this course.
> If your AWS account is already being used for other purposes, **proceed with caution**, as existing resources may be stopped or modified.

## Quick setup

1. Open the AWS CloudFormation console at https://console.aws.amazon.com/cloudformation
2. On the navigation bar at the top of the screen, choose the AWS Region to create the stack in.
3. On the **Stacks** page, choose **Create stack** at top right, and then choose **With new resources (standard)**.

On the **Create stack** page, do one of the following:

1. Choose **Choose an existing template**. Then, under **Specify template**, choose **Upload a template file**.
2. Download the `aws-learning-budget-keeper.yaml` template file from this repository to your local computer, then choose **Choose File** and select the downloaded file.
3. Once you have chosen your template, CloudFormation uploads the file and displays the S3 URL.
4. Choose **Next** to continue and to validate the template.
5. On the **Specify stack details** page, under **Stack name** type name to your stack, e.g. `aws-learning-budget-keeper`.
6. In the Parameters section, specify values for the following configurations:
   - **IAMGroup** - Name of the IAM group that you want to restrict. You should type the IAM group you created for your IAM user.
   - **AutoShutdownHours** - Times of day (in UTC) when instance shutdown automation should run.
   - **AllowedRegions** - List of AWS regions where you want the automation to operate.
7. Choose **Next**.
8. In the **Configure stack options** page, keep the default configurations, and choose **I acknowledge that this template may create IAM resources**.
9. Choose **Next** to continue.
10. On the **Review and create** page, review the details of your stack, and choose **Submit**.


## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│   Lambda        │───▶│   EC2/ASG       │
│   (Scheduler)   │    │   Function      │    │   Shutdown      │
└─────────────────┘    └─────────────────┘    └─────────────────┘ 
                  
```
