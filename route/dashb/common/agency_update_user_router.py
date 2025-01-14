from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
import boto3
import datetime

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_update_user_router = Blueprint('agency_update_user', __name__)

@agency_update_user_router.route('/agency_update_user', methods=['POST'])
def agency_update_user():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        required_fields = ['app_user_number', 'lastname', 'firstname', 'status', 'permission']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_error_response(
                f"必須パラメータが不足しています: {', '.join(missing_fields)}",
                None
            )), 400

        # パラメータの取得
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
                
                # 現在時刻を取得
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # m_user テーブルの更新
                update_user_query = """
                UPDATE m_user
                SET lastname = %s,
                    firstname = %s,
                    status = %s,
                    update_date = %s,
                    update_user = %s
                WHERE user_id = %s;
                """
                cursor.execute(update_user_query, (lastname, firstname, status, now, 'Dashboard', user_id))

                # m_user_agency テーブルの更新
                update_user_agency_query = """
                UPDATE m_user_agency
                SET permission = %s
                WHERE user_id = %s;
                """
                cursor.execute(update_user_agency_query, (permission, user_id))

                # statusが3の場合、Cognitoのアカウントを削除
                if status == 3:
                    # m_userからemailを取得
                    select_query = "SELECT mail FROM m_user WHERE user_id = %s"
                    cursor.execute(select_query, (user_id,))
                    result = cursor.fetchone()

                    if not result or not result['mail']:
                        return jsonify(create_error_response(
                            "指定されたユーザーのメールアドレスが見つかりません",
                            None
                        )), 404

                    email = result['mail']
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
                        "app_user_number": app_user_number,
                        "lastname": lastname,
                        "firstname": firstname
                    }
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ更新中にエラーが発生しました",
            str(e)
        )), 500
