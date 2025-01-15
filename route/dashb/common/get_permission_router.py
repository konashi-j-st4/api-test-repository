from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

get_permission_router = Blueprint('get_permission', __name__)

@get_permission_router.route('/get_permission', methods=['POST'])
def get_permission():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # パラメータの取得
        app_user_number = data.get('app_user_number')
        user_category = data.get('userCategory')

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                base_query = """
                SELECT permission_id, permission_name
                FROM m_permission
                """

                if user_category == 4:
                    where_clause = "WHERE permission_id BETWEEN 2 AND 7"
                elif app_user_number:
                    # user_idが指定されている場合、m_user_agencyからpermissionを取得
                    user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                    cursor.execute(user_id_query, (app_user_number,))
                    result = cursor.fetchone()
                    if not result:
                        return jsonify(create_error_response(
                            "指定されたapp_user_numberに対応するユーザーが見つかりません",
                            None
                        )), 404
                    user_id = result['user_id']
                    user_permission_query = """
                    SELECT permission FROM m_user_agency WHERE user_id = %s;
                    """
                    cursor.execute(user_permission_query, (user_id,))
                    user_permission = cursor.fetchone()

                    if user_permission:
                        permission = user_permission['permission']
                        where_clause = f"WHERE permission_id <= {permission} AND permission_id != 1"
                    else:
                        where_clause = "WHERE permission_id != 1"
                else:
                    where_clause = ""

                permission_query = f"{base_query} {where_clause} ORDER BY permission_id;"
                
                cursor.execute(permission_query)
                result = cursor.fetchall()
                

                return jsonify(create_success_response(
                    "権限情報を取得しました。" if result else "権限情報が存在しません。[E001]",
                    result if result else None
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500 