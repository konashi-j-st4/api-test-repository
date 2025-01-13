from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
import datetime
import random
import boto3
from botocore.exceptions import ClientError
import re

# RDS設定
db_user_name = os.environ['USER_NAME']
db_password = os.environ['PASSWORD']
end_point = os.environ['END_POINT']
db_name = os.environ['DB_NAME']
port = int(os.environ['PORT'])

# Cognito設定
COGNITO_USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognitoクライアントの初期化
cognito_client = boto3.client('cognito-idp')

def generate_unique_number(cursor, table, column, length):
    for _ in range(5):  # 5回まで試行
        number = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (number,))
        if cursor.fetchone()[0] == 0:
            return number
    raise ValueError(f"一意の{column}の生成に失敗しました（5回試行後）")

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
        raise ValueError(f"指定されたuser_id: {user_id}に対応するcorporate_idが見つかりません")
    return result[0]

corporate_user_register_router = Blueprint('corporate_user_register', __name__)

@corporate_user_register_router.route('/corporate_user_register', methods=['POST'])
def corporate_user_register():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの取得
        user_id = data.get('userId')
        corporate_id = data.get('corporateId')
        lastName = data.get('lastName')
        firstName = data.get('firstName')
        email = data.get('email')
        phone = data.get('phone')

        # パラメータのバリデーション
        if not (user_id or corporate_id):
            return jsonify(create_error_response(
                "userIdまたはcorporateIdのいずれかが必要です",
                None
            )), 400

        if not all([lastName, firstName, email, phone]):
            return jsonify(create_error_response(
                "lastName, firstName, email, phoneは必須項目です",
                None
            )), 400

        # MySQLに接続
        conn = pymysql.connect(
            host=end_point,
            user=db_user_name,
            passwd=db_password,
            db=db_name,
            port=port,
            connect_timeout=60
        )
        logger.info("データベースへの接続に成功しました")

        try:
            with conn.cursor() as cursor:
                # トランザクション開始
                conn.begin()

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
                user_id_new = result[0]

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
                        "user_id": user_id_new,
                        "app_user_number": app_user_number,
                        "cognito_username": cognito_username,
                        "ech_nav_code": ech_nav_code
                    }
                )), 200

        except Exception as e:
            conn.rollback()
            logger.error(f"データベース処理中にエラーが発生しました: {str(e)}")
            return jsonify(create_error_response(
                "ユーザー登録中にエラーが発生しました",
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