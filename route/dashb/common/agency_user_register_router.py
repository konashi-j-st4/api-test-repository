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
from utils.utils import format_phone_number, get_jst_now

# Cognito設定
COGNITO_USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognitoクライアントの初期化
cognito_client = boto3.client('cognito-idp')

# def generate_ech_nav_code(cursor, agency_id):
#     cursor.execute("""
#     SELECT COUNT(*) + 1 as sequence_number
#     FROM m_user u 
#     JOIN m_user_agency uc ON u.user_id = uc.user_id 
#     WHERE uc.agency_id = %s
#     """, (agency_id,))
#     sequence_number = cursor.fetchone()['sequence_number']
    
#     ech_nav_code = f"AGENEchNaviCD{agency_id}{sequence_number:04d}"
#     return ech_nav_code

def register_cognito_user(email, phone, lastName, firstName, ech_nav_code):
    try:
        formatted_phone = format_phone_number(phone)
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        
        response = cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=formatted_phone,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'phone_number', 'Value': formatted_phone},
                {'Name': 'family_name', 'Value': lastName},
                {'Name': 'given_name', 'Value': firstName},
                {'Name': 'custom:ech_nav_code', 'Value': ech_nav_code},
                {'Name': 'custom:user_category', 'Value': '4'},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'phone_number_verified', 'Value': 'false'}
            ],
            DesiredDeliveryMediums=['EMAIL']
        )

        cognito_client.admin_set_user_settings(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=formatted_phone,
            MFAOptions=[
                {
                    'DeliveryMedium': 'SMS',
                    'AttributeName': 'phone_number'
                }
            ]
        )
        
        logger.info(f"Cognitoへのユーザー登録が完了しました: {formatted_phone}")
        return response['User']['Username']
    except ClientError as e:
        logger.error(f"Cognitoへのユーザー登録中にエラーが発生しました: {str(e)}")
        raise

agency_user_register_router = Blueprint('agency_user_register', __name__)

@agency_user_register_router.route('/agency_user_register', methods=['POST'])
def agency_user_register():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # パラメータの取得
        app_user_number = data.get('app_user_number')
        agency_id = data.get('agencyId')
        lastName = data.get('lastName')
        firstName = data.get('firstName')
        email = data.get('email')
        phone = data.get('phone')
        permission = data.get('permission')

        # バリデーション
        if not (app_user_number or agency_id):
            return jsonify(create_error_response(
                "app_user_numberまたはagencyIdのいずれかが必要です",
                None
            )), 400

        if not all([lastName, firstName, email, phone, permission]):
            return jsonify(create_error_response(
                "lastName, firstName, email, phone, permissionは必須です",
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

                # agency_idの取得
                if not agency_id:
                    cursor.execute("SELECT agency_id FROM m_user_agency WHERE user_id = %s", (user_id,))
                    result = cursor.fetchone()
                    if not result:
                        return jsonify(create_error_response(
                            "指定されたユーザーIDに対応する企業IDが見つかりません",
                            None
                        )), 404
                    agency_id = result['agency_id']

                now = get_jst_now()
                app_user_number = generate_unique_number(cursor, 'm_user', 'app_user_number', 10)
                ech_nav_code = "EchNavi" + "AGE" + app_user_number

                # m_userテーブルにインサート
                insert_user_query = """
                INSERT INTO m_user (
                    echnavicode, app_user_number, user_category, lastname, firstname,
                    mail, create_date, create_user, update_date, update_user, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(insert_user_query, (
                    ech_nav_code, app_user_number, 4, lastName, firstName,
                    email, now, 'Dashboard', now, 'Dashboard', 1
                ))

                # 挿入したレコードのuser_idを取得
                cursor.execute("SELECT user_id FROM m_user WHERE app_user_number = %s", (app_user_number,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("ユーザーIDの取得に失敗しました")
                user_id_new = result['user_id']

                # m_user_agencyテーブルにインサート
                insert_agency_query = """
                INSERT INTO m_user_agency (user_id, agency_id, permission)
                VALUES (%s, %s, %s);
                """
                cursor.execute(insert_agency_query, (user_id_new, agency_id, permission))

                # Cognitoにユーザーを登録
                cognito_username = register_cognito_user(email, phone, lastName, firstName, ech_nav_code)
                logger.info(f"Cognitoへのユーザー登録が完了しました: {cognito_username}")

                conn.commit()
                logger.info("ユーザー情報の登録に成功しました")

                return jsonify(create_success_response(
                    "ユーザー情報の登録に成功しました",
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