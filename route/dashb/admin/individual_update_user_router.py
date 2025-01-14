from flask import Blueprint, jsonify, request
import logging
import pymysql
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

individual_update_user_router = Blueprint('individual_update_user', __name__)

@individual_update_user_router.route('/individual_update_user', methods=['POST'])
def individual_update_user():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['user_id', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        app_user_number = data['user_id']
        status = data['status']

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # app_user_numberからuser_idを取得
                user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                cursor.execute(user_id_query, (app_user_number,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Failed to retrieve the inserted user_id")
                user_id = result[0]
                
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # m_user テーブルの更新
                update_user_query = """
                UPDATE m_user
                SET status = %s,
                    update_date = %s,
                    update_user = %s
                WHERE user_id = %s;
                """
                cursor.execute(update_user_query, (status, now, 'Dashboard', user_id))

                # 更新された行数を確認
                if cursor.rowcount > 0:
                    logger.info(f"User {user_id} updated successfully.")
                    return jsonify(create_success_response(
                        "User data was successfully updated.",
                        {"user_id": user_id}
                    )), 200
                else:
                    logger.warning(f"No user found with ID: {user_id}")
                    return jsonify(create_error_response(
                        "No user found with the given ID.[E003]",
                        {"user_id": user_id}
                    )), 404

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while updating user.'
        return jsonify(create_error_response(err_msg, str(e))), 500
