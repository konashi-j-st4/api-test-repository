from flask import Blueprint, jsonify, request
import json
import logging
import pymysql
import os
import boto3
from botocore.exceptions import ClientError
import re
import hmac
import base64
import hashlib
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.utils import format_phone_number, calculate_secret_hash

# Logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognito client
cognito_client = boto3.client('cognito-idp')

agency_user_login_router = Blueprint('agency_user_login', __name__)

@agency_user_login_router.route('/agency_user_login', methods=['POST'])
def agency_user_login():
    try:
        # リクエストボディから情報を取得
        body = request.get_json()
        if not body:
            raise ValueError("リクエストボディが空です")

        if 'phoneNumber' not in body or 'password' not in body:
            raise ValueError("電話番号またはパスワードが必要です")

        phone_number = body['phoneNumber']
        password = body['password']

        formatted_phone = format_phone_number(phone_number)

        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        client_id = os.environ['COGNITO_CLIENT_ID']
        client_secret = os.environ['COGNITO_CLIENT_SECRET']

    except Exception as e:
        logger.error(f"パラメータまたは環境変数の取得に失敗しました: {str(e)}")
        return jsonify(create_error_response("パラメータまたは環境変数の取得に失敗しました", str(e))), 500

    # Authenticate with Cognito
    try:
        formatted_phone = format_phone_number(phone_number)
        secret_hash = calculate_secret_hash(formatted_phone, client_id, client_secret)

        # まず、ユーザーの状態を確認
        try:
            user_info = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=formatted_phone
            )
            
            # 電話番号の認証状態を確認
            attributes = {attr['Name']: attr['Value'] for attr in user_info['UserAttributes']}
            phone_verified = attributes.get('phone_number_verified', 'false')
            
            if phone_verified != 'true':
                logger.info("電話番号が未認証です")
                return jsonify(create_success_response(
                    "SMS認証が完了していません。初回ログインの方のリンクから認証を完了してください。",
                    None
                )), 200

            # 電話番号が認証済みの場合、認証を試行
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

            # echナビコードの取得
            ech_nav_code = next((attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'custom:ech_nav_code'), None)
            logger.info(f"Ech nav code: {ech_nav_code}")
            
            if not ech_nav_code:
                raise ValueError("custom:ech_nav_code not found in user attributes")

            # MySQLに接続して処理を続行
            try:
                with db.get_connection() as conn:
                    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                        user_query = """
                        SELECT app_user_number 
                        FROM m_user
                        WHERE echnavicode = %s
                        AND user_category = 4;
                        """
                        cursor.execute(user_query, (ech_nav_code,))
                        result = cursor.fetchone()
                        
                        if result:
                            return jsonify(create_success_response(
                                "ログインに成功しました",
                                {
                                    "app_user_number": result['app_user_number'],
                                    "accessToken": auth_response['AuthenticationResult']['AccessToken']
                                }
                            )), 200
                        else:
                            return jsonify(create_error_response(
                                "ユーザーが見つかりません[E002]",
                                None
                            )), 404

            except Exception as db_error:
                logger.error(f"データベースエラー: {str(db_error)}")
                return jsonify(create_error_response(
                    "データベース処理中にエラーが発生しました",
                    str(db_error)
                )), 500

        except cognito_client.exceptions.NotAuthorizedException:
            logger.info("電話番号またはパスワードが無効です[E001]")
            return jsonify(create_error_response(
                "電話番号またはパスワードが間違っています[E001]",
                None
            )), 401

        except cognito_client.exceptions.UserNotFoundException:
            logger.error("ユーザーが見つかりません")
            return jsonify(create_error_response(
                "ユーザーが見つかりません",
                None
            )), 404

    except ClientError as e:
        logger.error(f"Cognito エラー: {str(e)}")
        return jsonify(create_error_response(
            "認証処理中にエラーが発生しました",
            str(e)
        )), 500

    except Exception as e:
        logger.error(f"認証中にエラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "認証処理中にエラーが発生しました",
            str(e)
        )), 500 