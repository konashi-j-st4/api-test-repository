from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_get_users_router = Blueprint('corporate_get_users', __name__)

@corporate_get_users_router.route('/corporate_get_users', methods=['POST'])
def corporate_get_users():
    conn = None
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
        get_all_flg = data.get('getAllFlg', 0)  # デフォルト値は0

        if not app_user_number and get_all_flg != 1:
            return jsonify(create_error_response(
                "userIdは必須です（getAllFlgが1の場合を除く）",
                None
            )), 400

        # MySQLに接続
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("データベースへの接続に成功しました")

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if get_all_flg == 1:
                    # getAllFlgが1の場合、全件取得
                    user_query = """
                    SELECT a.user_id, a.app_user_number, a.lastname, a.firstname, a.status, 
                           b.permission, b.corporate_id, c.company
                    FROM m_user a
                    INNER JOIN m_user_corporate b ON a.user_id = b.user_id
                    INNER JOIN m_corporate c ON b.corporate_id = c.corporate_id
                    WHERE a.user_category = 2
                    AND a.status <> 3
                    ORDER BY b.corporate_id, a.user_id;
                    """
                    cursor.execute(user_query)
                else:
                    # app_user_numberからuser_idを取得
                    user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                    cursor.execute(user_id_query, (app_user_number,))
                    result = cursor.fetchone()
                    if not result:
                        return jsonify(create_error_response(
                            "指定されたapp_user_numberに対応するユーザーが見つかりません",
                            None
                        )), 404
                    user_id = result[0]
                    
                    # getAllFlgが1以外の場合、ユーザーIDに基づいて取得
                    user_query = """
                    SELECT a.user_id, a.app_user_number, a.lastname, a.firstname, a.status, b.permission 
                    FROM m_user a
                    INNER JOIN m_user_corporate b ON a.user_id = b.user_id
                    WHERE b.corporate_id = (
                        SELECT corporate_id 
                        FROM m_user_corporate 
                        WHERE user_id = %s
                    )   
                    AND a.user_category = 2
                    AND a.status <> 3;
                    """
                    cursor.execute(user_query, (user_id,))

                result = cursor.fetchall()
                logger.info("クエリの実行に成功しました")

                return jsonify(create_success_response(
                    "ユーザー情報を取得しました。" if result else "ユーザー情報が存在しません。[E001]",
                    result if result else None
                )), 200

        except Exception as e:
            logger.error(f"クエリ実行中にエラーが発生しました: {str(e)}")
            return jsonify(create_error_response(
                "クエリ実行中にエラーが発生しました",
                str(e)
            )), 500

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "パラメータまたは環境変数の取得に失敗しました",
            str(e)
        )), 500

    finally:
        if conn and conn.open:
            conn.close()
            logger.info("データベース接続を終了しました")