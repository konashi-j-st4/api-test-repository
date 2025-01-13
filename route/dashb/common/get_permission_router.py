from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

get_permission_router = Blueprint('get_permission', __name__)

@get_permission_router.route('/get_permission', methods=['POST'])
def get_permission():
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
        user_id = data.get('userId')
        user_category = data.get('userCategory')

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
                base_query = """
                SELECT permission_id, permission_name
                FROM m_permission
                """

                if user_category == 4:
                    where_clause = "WHERE permission_id BETWEEN 2 AND 7"
                elif user_id:
                    # user_idが指定されている場合、m_user_agencyからpermissionを取得
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
                
                logger.info(f"クエリの実行に成功しました: {permission_query}")
                logger.info(f"クエリ結果: {result}")

                return jsonify(create_success_response(
                    "権限情報を取得しました。" if result else "権限情報が存在しません。[E001]",
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