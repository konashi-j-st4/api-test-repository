from flask import Blueprint, jsonify, request
import logging
import pymysql
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_update_company_router = Blueprint('agency_update_company', __name__)

@agency_update_company_router.route('/agency_update_company', methods=['POST'])
def agency_update_company():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['agency_id', 'app_agency_number', 'company', 'zip_code', 
                         'prefecture', 'city', 'address', 'country', 'telephone', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        agency_id = data['agency_id']
        app_agency_number = data['app_agency_number']
        company = data['company']
        zip_code = data['zip_code']
        prefecture = data['prefecture']
        city = data['city']
        address = data['address']
        building = data.get('building', '')  # buildingは任意フィールド
        country = data['country']
        telephone = data['telephone']
        status = data['status']

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 実行クエリ
                update_query = """
                UPDATE m_agency
                SET app_agency_number = %s, company = %s, zip_code = %s, 
                    prefecture = %s, city = %s, address = %s, building = %s, 
                    country = %s, telephone = %s, status = %s, 
                    update_date = %s, update_user = %s
                WHERE agency_id = %s
                """
                cursor.execute(update_query, (
                    app_agency_number, company, zip_code, prefecture, city, 
                    address, building, country, telephone, status, now, 'Dashboard', agency_id
                ))

                # 更新された行数を確認
                if cursor.rowcount > 0:
                    logger.info(f"Agency {agency_id} updated successfully.")
                    return jsonify(create_success_response(
                        "Agency updated successfully.",
                        {"agency_id": agency_id}
                    )), 200
                else:
                    logger.warning(f"No agency found with ID: {agency_id}")
                    return jsonify(create_error_response(
                        "No agency found with the given ID.[E003]",
                        {"agency_id": agency_id}
                    )), 404

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while updating agency.'
        return jsonify(create_error_response(err_msg, str(e))), 500