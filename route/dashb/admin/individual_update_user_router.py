from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

individual_update_user_router = Blueprint('individual_update_user', __name__)

@individual_update_user_router.route('/individual_update_user', methods=['POST'])
def individual_update_user():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['user_id', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        user_id = data['user_id']
        status = data['status']

        # MySQLに接続
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("MySQL instance successfully connected to Database.")

        with conn.cursor() as cursor:
            # m_user テーブルの更新
            update_user_query = """
            UPDATE m_user
            SET status = %s,
                update_date = NOW(),
                update_user = 'API'
            WHERE user_id = %s;
            """
            cursor.execute(update_user_query, (status, user_id))
            
            # 変更を確定
            conn.commit()

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
        
        # エラーが発生した場合、DBをロールバック
        if conn and conn.open:
            conn.rollback()
            logger.info("Database transaction rolled back.")
        
        return jsonify(create_error_response(err_msg, str(e))), 500

    finally:
        if conn and conn.open:
            conn.close()
