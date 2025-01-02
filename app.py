import json
import logging
from flask import Flask
from route.router import router
import awsgi  # aws-wsgiをインポート

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.register_blueprint(router)

def lambda_handler(event, context):
    try:
        # API GatewayのイベントをFlaskで処理できる形に変換
        return awsgi.response(app, event, context)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': str(e)})
        }

if __name__ == '__main__':
    app.run(debug=True)