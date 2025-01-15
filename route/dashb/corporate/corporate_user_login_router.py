from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
import boto3
from botocore.exceptions import ClientError
from utils.utils import format_phone_number, calculate_secret_hash

# Logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognito client
cognito_client = boto3.client('cognito-idp')

corporate_user_login_router = Blueprint('corporate_user_login', __name__)

@corporate_user_login_router.route('/corporate_user_login', methods=['POST'])
def corporate_user_login():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの取得と検証
        phone_number = data.get('phoneNumber')
        password = data.get('password')
        
        if not phone_number or not password:
            return jsonify(create_error_response(
                "電話番号とパスワードは必須です",
                None
            )), 400

        # 環境変数の取得
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        client_id = os.environ['COGNITO_CLIENT_ID']
        client_secret = os.environ['COGNITO_CLIENT_SECRET']

        # Cognitoでの認証
        try:
            formatted_phone = format_phone_number(phone_number)
            secret_hash = calculate_secret_hash(formatted_phone, client_id, client_secret)

            auth_response = cognito_client.initiate_auth(
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': formatted_phone,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash
                },
                ClientId=client_id
            )
            logger.info("認証に成功しました")

            user_info = cognito_client.get_user(
                AccessToken=auth_response['AuthenticationResult']['AccessToken']
            )
            
            ech_nav_code = next((attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'custom:ech_nav_code'), None)
            logger.info(f"取得したEchNaviコード: {ech_nav_code}")
            
            if not ech_nav_code:
                return jsonify(create_error_response(
                    "ユーザー属性にEchNaviコードが見つかりません",
                    None
                )), 400

            # 電話番号の認証状態を確認
            phone_verified = next((attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'phone_number_verified'), 'false')
            if phone_verified != 'true':
                return jsonify(create_error_response(
                    "電話番号が未認証です。スマホアプリのechナビから認証を行ってください。",
                    None
                )), 400

        except ClientError as e:
            logger.error(f"Cognito認証エラー: {str(e)}")
            if e.response['Error']['Code'] == 'NotAuthorizedException':
                return jsonify(create_error_response(
                    "電話番号またはパスワードが正しくありません",
                    None
                )), 401
            return jsonify(create_error_response(
                "認証中にエラーが発生しました",
                str(e)
            )), 500

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                user_query = """
                SELECT app_user_number 
                FROM m_user
                WHERE echnavicode = %s
                AND user_category = 2;
                """
                cursor.execute(user_query, (ech_nav_code,))
                result = cursor.fetchone()
                
                if result:
                    return jsonify(create_success_response(
                        "ログインに成功しました",
                        {"app_user_number": result['app_user_number']}
                    )), 200
                else:
                    return jsonify(create_error_response(
                        "ユーザーが見つかりません[E002]",
                        None
                    )), 404

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500