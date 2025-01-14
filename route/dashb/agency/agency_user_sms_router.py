from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
import boto3
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import re
from db.db_connection import db

# Logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret_hash(username, client_id, client_secret):
    msg = username + client_id
    dig = hmac.new(bytes(client_secret, 'utf-8'), 
        msg = msg.encode('utf-8'), 
        digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2

def format_phone_number(phone):
    logger.info(f"元の電話番号: {phone}")

    # 数字以外の文字を削除
    digits_only = re.sub(r'\D', '', phone)
    
    # 日本の電話番号を想定
    if digits_only.startswith('0'):
        formatted = '+81' + digits_only[1:]
    elif digits_only.startswith('81'):
        formatted = '+' + digits_only
    else:
        formatted = '+81' + digits_only

    # E.164 形式の検証
    if not re.match(r'^\+81[1-9]\d{9}$', formatted):
        raise ValueError(f"電話番号のフォーマットが不正です: {formatted}")

    logger.info(f"フォーマット後の電話番号: {formatted}")
    return formatted

agency_user_sms_router = Blueprint('agency_user_sms', __name__)

@agency_user_sms_router.route('/agency_user_sms', methods=['POST'])
def agency_user_sms():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータのチェック
        if 'phoneNumber' not in data or 'functionType' not in data:
            return jsonify(create_error_response(
                "phoneNumberとfunctionTypeは必須パラメータです",
                None
            )), 400

        function_type = data['functionType']
        phone_number = data['phoneNumber']
        formatted_phone = format_phone_number(phone_number)
        logger.info(f"function_type: {function_type}")

        # function_typeごとの必須パラメータチェック
        if function_type == 0:
            # 初回認証時
            if not all(key in data for key in ['echNaviCode', 'initialPassword', 'newPassword']):
                return jsonify(create_error_response(
                    "初回認証時はechNaviCode、initialPassword、newPasswordが必須です",
                    None
                )), 400
            ech_navi_code = data['echNaviCode']
            initial_password = data['initialPassword']
            new_password = data['newPassword']
            
        elif function_type == 1:
            # SMS認証時
            if not all(key in data for key in ['echNaviCode', 'authCode', 'session']):
                return jsonify(create_error_response(
                    "SMS認証時はechNaviCode、authCode、sessionが必須です",
                    None
                )), 400
            ech_navi_code = data['echNaviCode']
            auth_code = data['authCode']
            
        elif function_type == 2:
            # SMS認証コード再送信
            if 'newPassword' not in data:
                return jsonify(create_error_response(
                    "SMS認証コード再送信時はnewPasswordが必須です",
                    None
                )), 400
            new_password = data['newPassword']
            ech_navi_code = None
            
        elif function_type == 3:
            # パスワード再設定のSMS送信時
            # 電話番号のみ必要（すでにチェック済み）
            ech_navi_code = None
            
        elif function_type == 4:
            # パスワード再設定のSMS認証時
            if not all(key in data for key in ['authCode', 'newPassword']):
                return jsonify(create_error_response(
                    "パスワード再設定時はauthCodeとnewPasswordが必須です",
                    None
                )), 400
            ech_navi_code = None
            auth_code = data['authCode']
            new_password = data['newPassword']
            
        else:
            return jsonify(create_error_response(
                f"無効なfunction_type: {function_type}",
                None
            )), 400

        # 環境変数の取得
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        client_id = os.environ['COGNITO_CLIENT_ID']
        client_secret = os.environ['COGNITO_CLIENT_SECRET']

        # Cognitoクライアントの作成
        cognito_client = boto3.client('cognito-idp')

        try:
            if function_type == 0:
                # 初回認証時の処理
                with db.get_connection() as conn:
                    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                        user_query = "SELECT app_user_number FROM m_user WHERE echnavicode = %s;"
                        cursor.execute(user_query, (ech_navi_code,))
                        result = cursor.fetchone()
                    
                if not result:
                    return jsonify(create_error_response(
                        "echナビコードが間違っています",
                        None
                    )), 404

                app_user_number = result['app_user_number']

                try:
                    # ユーザー情報の取得
                    response = cognito_client.admin_get_user(
                        UserPoolId=user_pool_id,
                        Username=formatted_phone
                    )
                    user_status = response['UserStatus']
                    attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
                    phone_verified = attributes.get('phone_number_verified', 'false')
                    
                    # 認証済みの場合
                    if phone_verified == 'true':
                        return jsonify(create_success_response(
                            "認証済みです",
                            None
                        )), 200
                    
                    # 初回パスワード変更が必要な場合
                    if user_status == 'FORCE_CHANGE_PASSWORD':
                        try:
                            # 初回認証
                            auth_response = cognito_client.initiate_auth(
                                ClientId=client_id,
                                AuthFlow='USER_PASSWORD_AUTH',
                                AuthParameters={
                                    'USERNAME': formatted_phone,
                                    'PASSWORD': initial_password,
                                    'SECRET_HASH': get_secret_hash(formatted_phone, client_id, client_secret)
                                }
                            )
                            
                            # パスワード変更処理
                            if auth_response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
                                response = cognito_client.respond_to_auth_challenge(
                                    ClientId=client_id,
                                    ChallengeName='NEW_PASSWORD_REQUIRED',
                                    Session=auth_response['Session'],
                                    ChallengeResponses={
                                        'USERNAME': formatted_phone,
                                        'NEW_PASSWORD': new_password,
                                        'SECRET_HASH': get_secret_hash(formatted_phone, client_id, client_secret),
                                        'USER_ID_FOR_SRP': formatted_phone
                                    }
                                )
                                
                                # SMS認証コードの送信
                                if response.get('ChallengeName') == 'SMS_MFA':
                                    return jsonify(create_success_response(
                                        "パスワードが変更され、SMS認証コードが送信されました",
                                        {"session": response['Session']}
                                    )), 200

                        except ClientError as e:
                            logger.error(f"パスワード変更エラー: {str(e)}")
                            return jsonify(create_error_response(
                                "前回の認証プロセスを中断されています。システム管理者にお問い合わせください。",
                                str(e)
                            )), 400
                    
                    # 初回パスワード変更が不要な場合（SMS認証コードの再送信）
                    try:
                        auth_response = cognito_client.initiate_auth(
                            ClientId=client_id,
                            AuthFlow='USER_PASSWORD_AUTH',
                            AuthParameters={
                                'USERNAME': formatted_phone,
                                'PASSWORD': new_password,
                                'SECRET_HASH': get_secret_hash(formatted_phone, client_id, client_secret)
                            }
                        )
                        
                        if auth_response.get('ChallengeName') == 'SMS_MFA':
                            return jsonify(create_success_response(
                                "SMS認証コードを送信しました",
                                {"session": auth_response['Session']}
                            )), 200
                    
                    except ClientError as e:
                        logger.error(f"認証エラー: {str(e)}")
                        return jsonify(create_error_response(
                            "前回の認証プロセスを中断されています。システム管理者にお問い合わせください。",
                            str(e)
                        )), 400

                except cognito_client.exceptions.UserNotFoundException:
                    logger.error("ユーザーが見つかりません")
                    return jsonify(create_error_response(
                        "ユーザーが見つかりません",
                        None
                    )), 404

            elif function_type == 1:
                # SMS認証時の処理
                with db.get_connection() as conn:
                    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                        user_query = "SELECT app_user_number FROM m_user WHERE echnavicode = %s;"
                        cursor.execute(user_query, (ech_navi_code,))
                        result = cursor.fetchone()
                    
                if not result:
                    return jsonify(create_error_response(
                        "echナビコードが間違っています",
                        None
                    )), 404
                
                app_user_number = result['app_user_number']

                try:
                    # SMS MFA チャレンジに応答
                    response = cognito_client.respond_to_auth_challenge(
                        ClientId=client_id,
                        ChallengeName='SMS_MFA',
                        Session=data['session'],
                        ChallengeResponses={
                            'USERNAME': formatted_phone,
                            'SMS_MFA_CODE': auth_code,
                            'SECRET_HASH': get_secret_hash(formatted_phone, client_id, client_secret)
                        }
                    )
                    
                    if 'AuthenticationResult' in response:
                        # MFA設定を非アクティブにする
                        try:
                            cognito_client.admin_set_user_settings(
                                UserPoolId=user_pool_id,
                                Username=formatted_phone,
                                MFAOptions=[]
                            )
                            logger.info('MFA設定を非アクティブにしました')
                        except ClientError as mfa_error:
                            logger.error(f"MFA設定の変更に失敗しました: {str(mfa_error)}")
                            return jsonify(create_error_response(
                                "MFA設定の変更に失敗しました",
                                str(mfa_error)
                            )), 500
                        
                        return jsonify(create_success_response(
                            "認証が完了しました",
                            {"user_id": app_user_number}
                        )), 200
                    else:
                        return jsonify(create_error_response(
                            "認証プロセスで予期しないエラーが発生しました",
                            None
                        )), 400
                
                except cognito_client.exceptions.CodeMismatchException:
                    return jsonify(create_error_response(
                        "無効な認証コードです",
                        None
                    )), 400
                
                except cognito_client.exceptions.ExpiredCodeException:
                    return jsonify(create_error_response(
                        "認証コードの有効期限が切れています",
                        None
                    )), 400
                
                except ClientError as e:
                    return jsonify(create_error_response(
                        "認証に失敗しました",
                        str(e)
                    )), 400

            elif function_type == 2:
                # SMS認証コード再送信
                try:
                    auth_response = cognito_client.initiate_auth(
                        ClientId=client_id,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={
                            'USERNAME': formatted_phone,
                            'PASSWORD': new_password,
                            'SECRET_HASH': get_secret_hash(formatted_phone, client_id, client_secret)
                        }
                    )

                    if auth_response.get('ChallengeName') == 'SMS_MFA':
                        return jsonify(create_success_response(
                            "SMS認証コードが再送信されました",
                            {"session": auth_response['Session']}
                        )), 200
                    else:
                        return jsonify(create_error_response(
                            "SMS認証コードの再送信に失敗しました",
                            None
                        )), 400

                except cognito_client.exceptions.UserNotFoundException:
                    return jsonify(create_error_response(
                        "ユーザーが見つかりません",
                        None
                    )), 404

            elif function_type == 3:
                # パスワード再設定のSMS送信
                try:
                    response = cognito_client.forgot_password(
                        ClientId=client_id,
                        SecretHash=get_secret_hash(formatted_phone, client_id, client_secret),
                        Username=formatted_phone
                    )
                    
                    return jsonify(create_success_response(
                        "パスワード再設定用のSMS認証コードを送信しました",
                        None
                    )), 200
                    
                except cognito_client.exceptions.UserNotFoundException:
                    return jsonify(create_error_response(
                        "ユーザーが見つかりません",
                        None
                    )), 404
                    
                except ClientError as e:
                    return jsonify(create_error_response(
                        "SMS送信中にエラーが発生しました",
                        str(e)
                    )), 400

            elif function_type == 4:
                # パスワード再設定のSMS認証
                try:
                    response = cognito_client.confirm_forgot_password(
                        ClientId=client_id,
                        SecretHash=get_secret_hash(formatted_phone, client_id, client_secret),
                        Username=formatted_phone,
                        ConfirmationCode=auth_code,
                        Password=new_password
                    )
                    
                    return jsonify(create_success_response(
                        "パスワードが正常に再設定されました",
                        None
                    )), 200
                    
                except cognito_client.exceptions.CodeMismatchException:
                    return jsonify(create_error_response(
                        "認証コードが正しくありません",
                        None
                    )), 400
                    
                except cognito_client.exceptions.ExpiredCodeException:
                    return jsonify(create_error_response(
                        "認証コードの有効期限が切れています",
                        None
                    )), 400
                    
                except cognito_client.exceptions.InvalidPasswordException:
                    return jsonify(create_error_response(
                        "パスワードの形式が正しくありません",
                        None
                    )), 400
                    
                except ClientError as e:
                    return jsonify(create_error_response(
                        "パスワード再設定中にエラーが発生しました",
                        str(e)
                    )), 400

        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            return jsonify(create_error_response(
                "予期せぬエラーが発生しました",
                str(e)
            )), 500

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "パラメータまたは環境変数の取得に失敗しました",
            str(e)
        )), 500