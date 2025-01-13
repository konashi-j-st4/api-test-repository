from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

corporate_get_companies_router = Blueprint('corporate_get_companies', __name__)

@corporate_get_companies_router.route('/corporate_get_companies', methods=['POST'])
def corporate_get_companies():
    conn = None
    try:
        # MySQLへの接続情報
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("MySQL instance successfully connected to Database.")

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 実行クエリ
            corporate_query = """
            SELECT corporate_id, app_corporate_number, company, zip_code, prefecture, 
                   city, address, building, country, telephone, status
            FROM m_corporate
            """
            cursor.execute(corporate_query)
            result = cursor.fetchall()
            logger.info(corporate_query)
            logger.info(result)

            if result:
                return jsonify(create_success_response(
                    "All corporate companies retrieved successfully.",
                    result
                )), 200
            else:
                return jsonify(create_success_response(
                    "No corporate companies found.[E002]",
                    []
                )), 200

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while fetching corporate companies.'
        
        if conn and conn.open:
            conn.rollback()
            logger.info("Database transaction rolled back.")
        
        return jsonify(create_error_response(err_msg, str(e))), 500

    finally:
        if conn and conn.open:
            conn.close()