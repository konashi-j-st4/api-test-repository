from flask import Blueprint, jsonify, request
import logging
import pymysql
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_get_companies_router = Blueprint('agency_get_companies', __name__)

@agency_get_companies_router.route('/agency_get_companies', methods=['POST'])
def agency_get_companies():
    try:
        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 実行クエリ
                agency_query = """
                SELECT agency_id, app_agency_number, company, zip_code, prefecture, 
                       city, address, building, country, telephone, status
                FROM m_agency
                """
                cursor.execute(agency_query)
                result = cursor.fetchall()
                logger.info(agency_query)
                logger.info(result)

                if result:
                    return jsonify(create_success_response(
                        "All agencies retrieved successfully.",
                        result
                    )), 200
                else:
                    return jsonify(create_success_response(
                        "No agencies found.[E002]",
                        []
                    )), 200

    except Exception as e:
        # エラーロギング
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while fetching agencies.'
        detail_err_msg = 'An error occurred while executing the query.'
        logger.error(f"{err_msg}:{detail_err_msg}")            
        return jsonify(create_error_response(err_msg, detail_err_msg)), 500