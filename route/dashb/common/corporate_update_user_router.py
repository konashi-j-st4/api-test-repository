from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_update_user_router = Blueprint('corporate_update_user', __name__)

@corporate_update_user_router.route('/corporate_update_user', methods=['POST'])
def corporate_update_user():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの取得と検証
        required_fields = ['app_user_number', 'lastname', 'firstname', 'status', 'permission']
        for field in required_fields:
            if field not in data:
                return jsonify(create_error_response(
                    f"{field}は必須パラメータです",
                    None
                )), 400

        app_user_number = data['app_user_number']
        lastname = data['lastname']
        firstname = data['firstname']
        status = data['status']
        permission = data['permission']

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # app_user_numberからuser_idを取得
                user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                cursor.execute(user_id_query, (app_user_number,))
                result = cursor.fetchone()
                if not result:
                    return jsonify(create_error_response(
                        "指定されたapp_user_numberに対応するユーザーが見つかりません",
                        None
                    )), 404
                user_id = result['user_id']
                
                # m_user テーブルの更新
                update_user_query = """
                UPDATE m_user
                SET lastname = %s, firstname = %s, status = %s
                WHERE user_id = %s;
                """
                cursor.execute(update_user_query, (lastname, firstname, status, user_id))

                # m_user_corporate テーブルの更新
                update_user_corporate_query = """
                UPDATE m_user_corporate
                SET permission = %s
                WHERE user_id = %s;
                """
                cursor.execute(update_user_corporate_query, (permission, user_id))

                # 変更をコミット
                conn.commit()
                logger.info("ユーザー情報の更新に成功しました")

                return jsonify(create_success_response(
                    "ユーザー情報を更新しました",
                    None
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ更新中にエラーが発生しました",
            str(e)
        )), 500 