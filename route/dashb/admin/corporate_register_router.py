from flask import Blueprint, jsonify, request
import logging
import pymysql
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.db_utils import generate_unique_number
from utils.utils import get_jst_now

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_register_router = Blueprint('corporate_register', __name__)

@corporate_register_router.route('/corporate_register', methods=['POST'])
def corporate_register():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['corporate', 'zip_code', 'prefecture', 'city', 'address', 'country', 'telephone']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        corporate = data['corporate']
        zip_code = data['zip_code']
        prefecture = data['prefecture']
        city = data['city']
        address = data['address']
        building = data.get('building')  # オプショナル
        country = data['country']
        telephone = data['telephone']

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                now = get_jst_now()
                app_corporate_number = generate_unique_number(cursor, 'm_corporate', 'app_corporate_number', 3)
                
                # m_corporateテーブルにインサート
                insert_corporate_query = """
                INSERT INTO m_corporate (app_corporate_number, company, zip_code, prefecture, city, address, building, country, telephone, create_date, create_user, update_date, update_user, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(insert_corporate_query, (app_corporate_number, corporate, zip_code, prefecture, city, address, building, country, telephone, now, 'admin', now, 'admin', 1))
                
                # 挿入したレコードのcorporate_idを取得
                select_corporate_id_query = "SELECT corporate_id FROM m_corporate WHERE app_corporate_number = %s;"
                cursor.execute(select_corporate_id_query, (app_corporate_number,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Failed to retrieve the inserted corporate_id")
                corporate_id = result['corporate_id']
                
                logger.info("Corporate data was successfully registered in the database.")
                return jsonify(create_success_response(
                    "Corporate data was successfully registered in the database.",
                    {
                        "corporate_id": corporate_id,
                        "app_corporate_number": app_corporate_number
                    }
                )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'An error occurred while registering the corporate.'
        return jsonify(create_error_response(err_msg, str(e))), 500