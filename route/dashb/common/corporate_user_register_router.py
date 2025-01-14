from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
import datetime
import boto3
from botocore.exceptions import ClientError
from utils.db_utils import generate_unique_number
from utils.utils import format_phone_number

# Cognito設定
COGNITO_USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognitoクライアントの初期化
cognito_client = boto3.client('cognito-idp')

def generate_ech_nav_code(cursor, corporate_id):
    cursor.execute("""
    SELECT COUNT(*) + 1 
    FROM m_user u 
    JOIN m_user_corporate uc ON u.user_id = uc.user_id 
    WHERE uc.corporate_id = %s
    """, (corporate_id,))
    sequence_number = cursor.fetchone()[0]
    
    ech_nav_code = f"CORPEchNaviCD{corporate_id}{sequence_number:04d}"
    return ech_nav_code

def register_cognito_user(email, phone, lastName, firstName, ech_nav_code):
    try:
        formatted_phone = format_phone_number(phone)
        response = cognito_client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=formatted_phone,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'phone_number', 'Value': formatted_phone},
                {'Name': 'family_name', 'Value': lastName},
                {'Name': 'given_name', 'Value': firstName},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'phone_number_verified', 'Value': 'false'},
                {'Name': 'custom:ech_nav_code', 'Value': ech_nav_code},
                {'Name': 'custom:user_category', 'Value': '2'}
            ],
            DesiredDeliveryMediums=['EMAIL']
        )
        # MFAを有効にし、SMSを必須に設定
        cognito_client.admin_set_user_settings(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=formatted_phone,
            MFAOptions=[
                {
                    'DeliveryMedium': 'SMS',
                    'AttributeName': 'phone_number'
                }
            ],
        )
        return response['User']['Username']
    except ClientError as e:
        logger.error(f"Cognitoへのユーザー登録中にエラーが発生しました: {str(e)}")
        raise

def get_corporate_id(cursor, user_id):
    cursor.execute("SELECT corporate_id FROM m_user_corporate WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"corporate_idが見つかりません")
    return result['corporate_id']

corporate_user_register_router = Blueprint('corporate_user_register', __name__)

@corporate_user_register_router.route('/corporate_user_register', methods=['POST'])
def corporate_user_register():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの取得
        app_user_number = data.get('app_user_number')
        corporate_id = data.get('corporateId')
        lastName = data.get('lastName')
        firstName = data.get('firstName')
        email = data.get('email')
        phone = data.get('phone')

        # パラメータのバリデーション
        if not (app_user_number or corporate_id):
            return jsonify(create_error_response(
                "app_user_numberまたはcorporateIdのいずれかが必要です",
                None
            )), 400

        if not all([lastName, firstName, email, phone]):
            return jsonify(create_error_response(
                "lastName, firstName, email, phoneは必須項目です",
                None
            )), 400

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

                # corporate_idが提供されていない場合、user_idから取得
                if not corporate_id:
                    corporate_id = get_corporate_id(cursor, user_id)

                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                app_user_number = generate_unique_number(cursor, 'm_user', 'app_user_number', 10)
                ech_nav_code = generate_ech_nav_code(cursor, corporate_id)

                # m_userテーブルにインサート
                insert_user_query = """
                INSERT INTO m_user (echnavicode, app_user_number, user_category, lastname, firstname, mail, 
                                  create_date, create_user, update_date, update_user, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(insert_user_query, (
                    ech_nav_code, app_user_number, 2, lastName, firstName, email,
                    now, 'Dashboard', now, 'Dashboard', 1
                ))

                # 挿入したレコードのuser_idを取得
                cursor.execute("SELECT user_id FROM m_user WHERE app_user_number = %s", (app_user_number,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("登録したユーザーIDの取得に失敗しました")
                user_id_new = result['user_id']

                # m_user_corporateテーブルにインサート
                insert_corporate_query = """
                INSERT INTO m_user_corporate (user_id, corporate_id, permission, password)
                VALUES (%s, %s, %s, %s);
                """
                cursor.execute(insert_corporate_query, (user_id_new, corporate_id, 1, 'default_password'))

                # Cognitoにユーザーを登録
                cognito_username = register_cognito_user(email, phone, lastName, firstName, ech_nav_code)
                logger.info(f"Cognitoへのユーザー登録が完了しました: {cognito_username}")

                # コミット
                conn.commit()
                logger.info("データベースとCognitoへのユーザー登録が完了しました")

                return jsonify(create_success_response(
                    "ユーザー登録が完了しました",
                    {
                        "app_user_number": app_user_number,
                        "cognito_username": cognito_username,
                        "ech_nav_code": ech_nav_code
                    }
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ登録中にエラーが発生しました",
            str(e)
        )), 500 