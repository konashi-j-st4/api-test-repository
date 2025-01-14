from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_get_users_router = Blueprint('agency_get_users', __name__)

@agency_get_users_router.route('/agency_get_users', methods=['POST'])
def agency_get_users():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # パラメータの取得
        app_user_number = data.get('userId')
        get_all_flg = data.get('getAllFlg')
        get_company_users_flg = data.get('getCompanyUsersFlg')

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
                
                if get_all_flg == 1:
                    # getAllFlgが1の場合のクエリ
                    user_query = """
                    SELECT a.user_id, a.app_user_number, a.lastname, a.firstname, a.status, b.permission, c.company
                    FROM m_user a
                    INNER JOIN m_user_agency b ON a.user_id = b.user_id
                    INNER JOIN m_agency c ON b.agency_id = c.agency_id
                    WHERE a.user_category = 4 
                    AND a.status <> 3
                    ORDER BY b.agency_id, a.user_id;
                    """
                    cursor.execute(user_query)
                elif get_company_users_flg == 1:
                    # getCompanyUsersFlgが1の場合のクエリ
                    user_query = """
                    SELECT a.user_id, a.app_user_number, a.lastname, a.firstname, a.status, b.permission 
                    FROM m_user a
                    INNER JOIN m_user_agency b ON a.user_id = b.user_id
                    WHERE b.agency_id = (
                        SELECT agency_id 
                        FROM m_user_agency 
                        WHERE user_id = %s
                    )   
                    AND a.user_category = 4
                    AND a.status <> 3;
                    """
                    cursor.execute(user_query, (user_id,))
                else:
                    # getCompanyUsersFlgが1以外、かつgetAllFlgが1以外の場合のクエリ
                    user_query = """
                    SELECT a.user_id, a.app_user_number, a.lastname, a.firstname, a.user_category, a.status, b.permission, c.permission_name
                    FROM m_user a
                    INNER JOIN m_user_agency b ON a.user_id = b.user_id
                    INNER JOIN m_permission c ON b.permission = c.permission_id
                    WHERE a.user_id = %s
                    AND a.status <> 3;
                    """
                    cursor.execute(user_query, (user_id,))

                result = cursor.fetchall() 
                logger.info(f"クエリの実行に成功しました: {user_query}")
                logger.info(f"クエリ結果: {result}")

                return jsonify(create_success_response(
                    "ユーザー情報を取得しました。" if result else "ユーザー情報が存在しません。[E001]",
                    result if result else None
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500