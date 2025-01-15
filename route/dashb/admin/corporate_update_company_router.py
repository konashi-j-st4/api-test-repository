from flask import Blueprint, jsonify, request
import logging
import pymysql
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.utils import get_jst_now

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_update_company_router = Blueprint('corporate_update_company', __name__)

@corporate_update_company_router.route('/corporate_update_company', methods=['POST'])
def corporate_update_company():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        
        # 必須フィールドの取得と検証
        required_fields = ['corporate_id', 'app_corporate_number', 'company', 'zip_code', 
                         'prefecture', 'city', 'address', 'country', 'telephone', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        corporate_id = data['corporate_id']
        app_corporate_number = data['app_corporate_number']
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
                now = get_jst_now()
                # 実行クエリ
                update_query = """
                UPDATE m_corporate
                SET app_corporate_number = %s, company = %s, zip_code = %s, 
                    prefecture = %s, city = %s, address = %s, building = %s, 
                    country = %s, telephone = %s, status = %s, 
                    update_date = %s, update_user = %s
                WHERE corporate_id = %s
                """
                cursor.execute(update_query, (
                    app_corporate_number, company, zip_code, prefecture, city, 
                    address, building, country, telephone, status, now, 'Dashboard', corporate_id
                ))

                # 更新された行数を確認
                if cursor.rowcount > 0:
                    logger.info(f"Corporate {corporate_id} updated successfully.")
                    return jsonify(create_success_response(
                        "Corporate updated successfully.",
                        {"corporate_id": corporate_id}
                    )), 200
                else:
                    logger.warning(f"No corporate found with ID: {corporate_id}")
                    return jsonify(create_error_response(
                        "No corporate found with the given ID.[E003]",
                        {"corporate_id": corporate_id}
                    )), 404

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while updating corporate.'
        return jsonify(create_error_response(err_msg, str(e))), 500