"""
AWS Resource Governor Lambda Function

This function automatically manages AWS resources to control costs and enforce governance:
- Stops running EC2 instances (except protected ones)
- Scales down Auto Scaling Groups to zero

"""

import boto3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    print(f"Resource Governor Lambda triggered at {datetime.now(timezone.utc)}")
    
    # Get allowed regions from environment variable
    allowed_regions = get_allowed_regions()
    print(f"Processing resource governance across regions: {allowed_regions}")
    
    # Aggregate results across all regions
    aggregate_results = {
        'stopped_instances': [],
        'scaled_down_asgs': [],
        'errors': [],
        'regions_processed': []
    }
    
    # Process each allowed region
    for region in allowed_regions:
        try:
            print(f"Processing region: {region}")
            region_results = process_region(region)
            
            # Aggregate results
            aggregate_results['stopped_instances'].extend(region_results['stopped_instances'])
            aggregate_results['scaled_down_asgs'].extend(region_results['scaled_down_asgs'])
            aggregate_results['errors'].extend(region_results['errors'])
            aggregate_results['regions_processed'].append(region)
            
        except Exception as e:
            error_msg = f"Error processing region {region}: {str(e)}"
            print(error_msg)
            aggregate_results['errors'].append(error_msg)

    return {
        'statusCode': 200,
        'body': json.dumps(aggregate_results)
    }


def get_allowed_regions() -> List[str]:
    """
    Get the list of allowed regions from environment variable.
    
    Returns:
        List of allowed AWS region names
    """
    allowed_regions_str = os.environ.get('ALLOWED_REGIONS', 'us-east-1')
    regions = [region.strip() for region in allowed_regions_str.split(',') if region.strip()]
    return regions


def process_region(region: str) -> Dict[str, List[str]]:
    """
    Process resource governance for a specific region.
    
    Args:
        region: AWS region name
        
    Returns:
        Dict containing regional results
    """
    print(f"Initializing AWS clients for region: {region}")
    
    # Initialize region-specific AWS clients
    ec2 = boto3.client('ec2', region_name=region)
    autoscaling = boto3.client('autoscaling', region_name=region)
    
    region_results = {
        'stopped_instances': [],
        'scaled_down_asgs': [],
        'errors': []
    }
    
    try:
        # 1. Stop running EC2 instances (except those with specific tags)
        stopped_instances = stop_idle_instances(ec2, region)
        region_results['stopped_instances'] = stopped_instances
        
        # 2. Scale down Auto Scaling Groups to zero
        scaled_down_asgs = scale_down_asgs(autoscaling, region)
        region_results['scaled_down_asgs'] = scaled_down_asgs
        
        print(f"Region {region} processing completed - Instances: {len(stopped_instances)}, ASGs: {len(scaled_down_asgs)}")
        
    except Exception as e:
        error_msg = f"Error processing region {region}: {str(e)}"
        print(error_msg)
        region_results['errors'].append(error_msg)
    
    return region_results


def is_instance_stop_protected(ec2, instance_id: str) -> bool:
    """
    Check if an EC2 instance has stop protection enabled via API or custom tags.
    
    Args:
        ec2: Boto3 EC2 client
        instance_id: EC2 instance ID
        
    Returns:
        True if instance has stop protection, False otherwise
    """
    try:
        # Check API stop protection
        response = ec2.describe_instance_attribute(
            InstanceId=instance_id,
            Attribute='disableApiStop'
        )
        if response.get('DisableApiStop', {}).get('Value', False):
            return True
        
        # Check custom ResourceGovernance tag
        tags_response = ec2.describe_tags(
            Filters=[
                {'Name': 'resource-id', 'Values': [instance_id]},
                {'Name': 'key', 'Values': ['ResourceGovernance']}
            ]
        )
        
        for tag in tags_response.get('Tags', []):
            if tag.get('Value', '').lower() == 'keep':
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking stop protection for instance {instance_id}: {str(e)}")
        # If we can't determine protection status, assume it's protected to be safe
        return True


def is_asg_protected(autoscaling, asg_name: str) -> bool:
    """
    Check if an Auto Scaling Group has protection via custom tags.
    
    Args:
        autoscaling: Boto3 Auto Scaling client
        asg_name: Auto Scaling Group name
        
    Returns:
        True if ASG has protection, False otherwise
    """
    try:
        response = autoscaling.describe_tags(
            Filters=[
                {'Name': 'auto-scaling-group', 'Values': [asg_name]},
                {'Name': 'key', 'Values': ['ResourceGovernance']}
            ]
        )
        
        for tag in response.get('Tags', []):
            if tag.get('Value', '').lower() == 'keep':
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking protection for ASG {asg_name}: {str(e)}")
        # If we can't determine protection status, assume it's protected to be safe
        return True


def stop_idle_instances(ec2, region: str) -> List[str]:
    """
    Stop all running EC2 instances except those with stop protection enabled.
    
    Args:
        ec2: Boto3 EC2 client
        region: AWS region name
        
    Returns:
        List of stopped instance IDs
    """
    stopped_instances = []
    
    try:
        # Get all running instances
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance.get('InstanceType', 'unknown')
                
                # Check if instance has stop protection
                if is_instance_stop_protected(ec2, instance_id):
                    print(f"Skipping protected instance: {instance_id} (type: {instance_type}) in region {region}")
                    continue
                
                try:
                    ec2.stop_instances(InstanceIds=[instance_id])
                    stopped_instances.append(f"{instance_id} ({region})")
                    print(f"Stopped instance: {instance_id} (type: {instance_type}) in region {region}")
                except Exception as e:
                    error_msg = f"Failed to stop instance {instance_id} in {region}: {str(e)}"
                    print(error_msg)

    except Exception as e:
        print(f"Error stopping instances in {region}: {str(e)}")
    
    return stopped_instances


def scale_down_asgs(autoscaling, region: str) -> List[str]:
    """
    Scale down all Auto Scaling Groups to zero capacity except protected ones.
    
    Args:
        autoscaling: Boto3 Auto Scaling client
        region: AWS region name
        
    Returns:
        List of scaled down ASG names
    """
    scaled_down_asgs = []
    
    try:
        # Get all Auto Scaling Groups
        paginator = autoscaling.get_paginator('describe_auto_scaling_groups')
        
        for page in paginator.paginate():
            for asg in page['AutoScalingGroups']:
                asg_name = asg['AutoScalingGroupName']
                current_capacity = asg['DesiredCapacity']
                
                # Check if ASG is protected
                if is_asg_protected(autoscaling, asg_name):
                    print(f"Skipping protected ASG: {asg_name} (capacity: {current_capacity}) in region {region}")
                    continue
                
                if current_capacity > 0:
                    try:
                        autoscaling.update_auto_scaling_group(
                            AutoScalingGroupName=asg_name,
                            MinSize=0,
                            MaxSize=asg['MaxSize'],
                            DesiredCapacity=0
                        )
                        scaled_down_asgs.append(f"{asg_name} ({region})")
                        print(f"Scaled down ASG: {asg_name} (from {current_capacity} to 0) in region {region}")
                    except Exception as e:
                        error_msg = f"Failed to scale down ASG {asg_name} in {region}: {str(e)}"
                        print(error_msg)
                else:
                    print(f"ASG already at zero capacity: {asg_name} in region {region}")
    
    except Exception as e:
        print(f"Error scaling down ASGs in {region}: {str(e)}")
    
    return scaled_down_asgs
