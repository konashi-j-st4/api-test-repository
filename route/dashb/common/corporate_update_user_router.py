from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_update_user_router = Blueprint('corporate_update_user', __name__)

@corporate_update_user_router.route('/corporate_update_user', methods=['POST'])
def corporate_update_user():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの取得と検証
        required_fields = ['user_id', 'lastname', 'firstname', 'status', 'permission']
        for field in required_fields:
            if field not in data:
                return jsonify(create_error_response(
                    f"{field}は必須パラメータです",
                    None
                )), 400

        app_user_number = data['user_id']
        lastname = data['lastname']
        firstname = data['firstname']
        status = data['status']
        permission = data['permission']

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
            with conn.cursor() as cursor:
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