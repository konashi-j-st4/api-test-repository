from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
import boto3

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_update_user_router = Blueprint('agency_update_user', __name__)

@agency_update_user_router.route('/agency_update_user', methods=['POST'])
def agency_update_user():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        required_fields = ['user_id', 'lastname', 'firstname', 'status', 'permission']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_error_response(
                f"必須パラメータが不足しています: {', '.join(missing_fields)}",
                None
            )), 400

        # パラメータの取得
        user_id = data['user_id']
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
                # m_user テーブルの更新
                update_user_query = """
                UPDATE m_user
                SET lastname = %s,
                    firstname = %s,
                    status = %s,
                    update_date = NOW(),
                    update_user = 'API'
                WHERE user_id = %s;
                """
                cursor.execute(update_user_query, (lastname, firstname, status, user_id))

                # m_user_agency テーブルの更新
                update_user_agency_query = """
                UPDATE m_user_agency
                SET permission = %s,
                    update_date = NOW(),
                    update_user = 'API'
                WHERE user_id = %s;
                """
                cursor.execute(update_user_agency_query, (permission, user_id))

                # statusが3の場合、Cognitoのアカウントを削除
                if status == 3:
                    # m_userからemailを取得
                    select_query = "SELECT mail FROM m_user WHERE user_id = %s"
                    cursor.execute(select_query, (user_id,))
                    result = cursor.fetchone()

                    if not result or not result[0]:
                        return jsonify(create_error_response(
                            "指定されたユーザーのメールアドレスが見つかりません",
                            None
                        )), 404

                    email = result[0]
                    cognito_client = boto3.client('cognito-idp')
                    user_pool_id = os.environ['COGNITO_USER_POOL_ID']

                    try:
                        # Cognitoからユーザー情報を取得
                        list_users_response = cognito_client.list_users(
                            UserPoolId=user_pool_id,
                            Filter=f'email = \"{email}\"'
                        )

                        users = list_users_response.get('Users', [])
                        if not users:
                            logger.warning(f"Cognitoにユーザーが見つかりません: {email}")
                        elif len(users) > 1:
                            logger.warning(f"複数のCognitoユーザーが見つかりました: {email}")
                        else:
                            cognito_username = users[0]['Username']
                            # Cognitoのユーザーを削除
                            cognito_client.admin_delete_user(
                                UserPoolId=user_pool_id,
                                Username=cognito_username
                            )
                            logger.info(f"Cognitoユーザーの削除に成功しました: {cognito_username}")

                    except Exception as e:
                        logger.error(f"Cognito処理中にエラーが発生しました: {str(e)}")
                        # Cognito処理のエラーはDBの更新には影響を与えない
                        pass

                # 変更をコミット
                conn.commit()
                logger.info("ユーザー情報の更新に成功しました")

                return jsonify(create_success_response(
                    "ユーザー情報の更新に成功しました",
                    {
                        "user_id": user_id,
                        "lastname": lastname,
                        "firstname": firstname
                    }
                )), 200

        except Exception as e:
            logger.error(f"クエリ実行中にエラーが発生しました: {str(e)}")
            if conn and conn.open:
                conn.rollback()
                logger.info("トランザクションをロールバックしました")
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
