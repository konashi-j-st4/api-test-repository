from flask import Blueprint, jsonify
import json

dashboard_user_router = Blueprint('dashboard_user', __name__)

@dashboard_user_router.route('/user', methods=['GET'])
def user_home():
    try:
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Hello world!'
            })
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }), 500
