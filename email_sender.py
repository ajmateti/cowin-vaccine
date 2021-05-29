import boto3
import json

def send_email(topic, message, subject):
    client = boto3.client('sns')
    response = client.publish(
        TopicArn=topic,
        Message=message,
        Subject=subject,
        MessageAttributes={
            'DefaultSMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }
        }
    )
    return response