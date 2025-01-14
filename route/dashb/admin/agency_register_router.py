from flask import Blueprint, jsonify, request
import logging
import pymysql
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.db_utils import generate_unique_number

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_register_router = Blueprint('agency_register', __name__)

@agency_register_router.route('/agency_register', methods=['POST'])
def agency_register():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['agency', 'zip_code', 'prefecture', 'city', 'address', 'country', 'telephone']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        agency = data['agency']
        zip_code = data['zip_code']
        prefecture = data['prefecture']
        city = data['city']
        address = data['address']
        building = data.get('building')  # オプショナル
        country = data['country']
        telephone = data['telephone']

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                app_agency_number = generate_unique_number(cursor, 'm_agency', 'app_agency_number', 3)
                
                # m_agencyテーブルにインサート
                insert_agency_query = """
                INSERT INTO m_agency (app_agency_number, company, zip_code, prefecture, city, address, building, country, telephone, create_date, create_user, update_date, update_user, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(insert_agency_query, (app_agency_number, agency, zip_code, prefecture, city, address, building, country, telephone, now, 'admin', now, 'admin', 1))
                
                # 挿入したレコードのagency_idを取得
                select_agency_id_query = "SELECT agency_id FROM m_agency WHERE app_agency_number = %s;"
                cursor.execute(select_agency_id_query, (app_agency_number,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Failed to retrieve the inserted agency_id")
                agency_id = result['agency_id']
                
                logger.info("Agency data was successfully registered in the database.")
                return jsonify(create_success_response(
                    "Agency data was successfully registered in the database.",
                    {
                        "agency_id": agency_id,
                        "app_agency_number": app_agency_number
                    }
                )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'An error occurred while registering the agency.'
        return jsonify(create_error_response(err_msg, str(e))), 500