from flask import Blueprint, jsonify
import json

hello_world_router = Blueprint('hello_world', __name__)

@hello_world_router.route('/hello_world', methods=['GET'])
def user_home():
    try:
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Hello world!!'
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
