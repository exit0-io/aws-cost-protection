# AWS Resource Governor

An automated resource management and cost control system for AWS accounts that helps prevent unexpected charges through resource monitoring, automatic shutdowns, and policy enforcement.

## Features

- 🛑 **Automated Resource Management**: Stops EC2 instances and scales down ASGs twice daily
- 🔒 **IAM Policies**: Restricts expensive instance types and services
- 🌍 **Region Controls**: Limits resource creation to specified regions

## Quick Start

TBD

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `NotificationEmail` | String | Required | Email address for billing alerts |
| `IAMGroupToProtect` | String | `students` | Name of the IAM group to apply resource governance policies |
| `AllowedRegions` | CommaDelimitedList | `us-east-1,us-west-2,eu-west-1,eu-central-1` | AWS regions where resources can be created |


## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│   Lambda        │
│   (Scheduler)   │    │   Function      │
└─────────────────┘    └─────────────────┘
                              │           
                              ▼           
                       ┌─────────────────┐
                       │   EC2/ASG       │
                       │   Management    │
                       └─────────────────┘ 
```


## License

This project is open source and available under the [MIT License](LICENSE).

