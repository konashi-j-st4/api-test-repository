from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_update_company_router = Blueprint('agency_update_company', __name__)

@agency_update_company_router.route('/agency_update_company', methods=['POST'])
def agency_update_company():
    conn = None
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

        # MySQLに接続
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("MySQL instance successfully connected to Database.")

        with conn.cursor() as cursor:
            # 実行クエリ
            update_query = """
            UPDATE m_agency
            SET app_agency_number = %s, company = %s, zip_code = %s, 
                prefecture = %s, city = %s, address = %s, building = %s, 
                country = %s, telephone = %s, status = %s, 
                update_date = NOW(), update_user = 'API'
            WHERE agency_id = %s
            """
            cursor.execute(update_query, (
                app_agency_number, company, zip_code, prefecture, city, 
                address, building, country, telephone, status, agency_id
            ))
            
            # 変更を確定
            conn.commit()

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
        
        # 変更をロールバック
        if conn and conn.open:
            conn.rollback()
            logger.info("Database transaction rolled back.")
        
        return jsonify(create_error_response(err_msg, str(e))), 500

    finally:
        if conn and conn.open:
            conn.close()