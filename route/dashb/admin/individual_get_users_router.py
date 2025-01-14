from flask import Blueprint, jsonify, request
import logging
import pymysql
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

individual_get_users_router = Blueprint('individual_get_users', __name__)

@individual_get_users_router.route('/individual_get_users', methods=['POST'])
def individual_get_users():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        email = data.get('email')  # メールアドレスは任意パラメータ

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if email:
                    # メールアドレスが指定されている場合、該当ユーザーを取得
                    user_query = """
                    SELECT a.app_user_number, a.lastname, a.firstname, a.status, a.mail
                    FROM m_user a
                    INNER JOIN m_user_general b ON a.user_id = b.user_id
                    WHERE a.user_category = 1 
                    AND a.mail = %s
                    AND a.status <> 3
                    ORDER BY a.user_id desc;
                    """
                    cursor.execute(user_query, (email,))
                else:
                    # メールアドレスが指定されていない場合、全件取得
                    user_query = """
                    SELECT a.app_user_number, a.lastname, a.firstname, a.status, a.mail
                    FROM m_user a
                    INNER JOIN m_user_general b ON a.user_id = b.user_id
                    WHERE a.user_category = 1
                    AND a.status <> 3
                    ORDER BY a.user_id desc;
                    """
                    cursor.execute(user_query)

                result = cursor.fetchall()
                logger.info(user_query)
                logger.info(result)

                if result:
                    return jsonify(create_success_response(
                        "Users retrieved successfully.",
                        result
                    )), 200
                else:
                    return jsonify(create_success_response(
                        "No users found.",
                        []
                    )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while retrieving users.'
        return jsonify(create_error_response(err_msg, str(e))), 500 