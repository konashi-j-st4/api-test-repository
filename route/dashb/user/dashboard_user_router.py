from flask import Blueprint
import json
dashboard_user_router = Blueprint('dashboard_user', __name__)

@dashboard_user_router.route('/user', methods=['GET'])
def user_home():
    return {
        'statusCode': 200,
        'body': json.dumps('Hello world!')
    }
