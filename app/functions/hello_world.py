import json

def lambda_handler(event, context):

# テスト用2
    return {
        'statusCode': 200,
        'body': json.dumps('Hello world!')
    }