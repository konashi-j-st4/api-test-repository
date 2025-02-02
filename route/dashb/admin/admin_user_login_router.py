from flask import Blueprint, jsonify, request
import json
import logging
import pymysql
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

admin_user_login_router = Blueprint('admin_user_login', __name__)

@admin_user_login_router.route('/admin_user_login', methods=['POST'])
def admin_user_login():
    try:
        # リクエストボディから情報を取得
        body = request.get_json()
        
        if 'app_user_number' in body and 'password' in body:
            app_user_number = body['app_user_number']
            password = body['password']
        else:
            raise ValueError("app_user_number or password is missing in the request body")
            
    except Exception as e:
        err_msg = 'Failed to retrieve query parameters or environment variables'
        logger.error(f"{err_msg}:{str(e)}")
        return jsonify(create_error_response(err_msg, str(e))), 500

    try:
        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                user_query = """
                SELECT a.app_user_number 
                FROM m_user a
                INNER JOIN m_user_admin b ON a.user_id = b.user_id
                WHERE a.app_user_number = %s
                AND b.password = %s
                AND a.user_category = 3;
                """
                cursor.execute(user_query, (app_user_number, password))
                result = cursor.fetchone()
                
                if result:
                    return jsonify(create_success_response(
                        "You can reset your password.",
                        {"app_user_number": result['app_user_number']}
                    )), 200
                else:
                    return jsonify(create_success_response(
                        "User does not exist.[E001]",
                        None
                    )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'err.'
        detail_err_msg = 'An error occurred while executing the query.'
        logger.error(f"{err_msg}:{detail_err_msg}")
        return jsonify(create_error_response(err_msg, detail_err_msg)), 500
