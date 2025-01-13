from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
import boto3
from botocore.exceptions import ClientError
import re
import hmac
import base64
import hashlib

# Logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognito client
cognito_client = boto3.client('cognito-idp')

def calculate_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), 
                   msg=message.encode('utf-8'), 
                   digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

def format_phone_number(phone):
    logger.info(f"元の電話番号: {phone}")
    digits_only = re.sub(r'\D', '', phone)
    
    if digits_only.startswith('0'):
        formatted = '+81' + digits_only[1:]
    elif digits_only.startswith('81'):
        formatted = '+' + digits_only
    else:
        formatted = '+81' + digits_only

    if not re.match(r'^\+81[1-9]\d{9}$', formatted):
        raise ValueError(f"電話番号のフォーマットが不正です: {formatted}")

    logger.info(f"フォーマット後の電話番号: {formatted}")
    return formatted

corporate_user_login_router = Blueprint('corporate_user_login', __name__)

@corporate_user_login_router.route('/corporate_user_login', methods=['POST'])
def corporate_user_login():
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
                    "電話番号が未認証です",
                    None
                )), 400

        except ClientError as e:
            logger.error(f"Cognito認証エラー: {str(e)}")
            if e.response['Error']['Code'] == 'NotAuthorizedException':
                return jsonify(create_error_response(
                    "電話番号またはパスワードが正しくありません[E001]",
                    None
                )), 401
            return jsonify(create_error_response(
                "認証中にエラーが発生しました",
                str(e)
            )), 500

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
                user_query = """
                SELECT user_id 
                FROM m_user
                WHERE echnavicode = %s
                AND user_category = 2;
                """
                cursor.execute(user_query, (ech_nav_code,))
                result = cursor.fetchone()
                
                if result:
                    return jsonify(create_success_response(
                        "ログインに成功しました",
                        {"user_id": result['user_id']}
                    )), 200
                else:
                    return jsonify(create_error_response(
                        "ユーザーが見つかりません[E002]",
                        None
                    )), 404

        except Exception as e:
            logger.error(f"データベースクエリ実行中にエラーが発生しました: {str(e)}")
            return jsonify(create_error_response(
                "データベースクエリ実行中にエラーが発生しました",
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