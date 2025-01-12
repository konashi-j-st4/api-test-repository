from flask import Blueprint, jsonify, request
import logging
import pymysql
import os

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

agency_get_companies_router = Blueprint('agency_get_companies', __name__)

@agency_get_companies_router.route('/agency_get_companies', methods=['POST'])
def agency_get_companies():
    # エラーレスポンスは予め作成
    err_res = {
        "resultCode": "error",
        "data": {}
    }

    try:
        # MySQLへの接続情報
        db_user_name = os.environ['USER_NAME']
        db_password = os.environ['PASSWORD']
        end_point = os.environ['END_POINT']
        db_name = os.environ['DB_NAME']
        port = int(os.environ['PORT'])
    except Exception as e:
        err_msg = 'Failed to retrieve environment variables'
        err_res['message'] = err_msg
        err_res['data']['error'] = str(e)
        logger.error(f"{err_msg}:{str(e)}")
        return (err_res, 500)

    # MySQLに接続
    try:
        conn = pymysql.connect(host=end_point, user=db_user_name,
                               passwd=db_password, db=db_name, port=port, connect_timeout=60)
        logger.info("MySQL instance successfully connected to Database.")
    except Exception as e:
        err_msg = "MySQL instance failed to connect to Database."
        err_res['message'] = err_msg
        err_res['data']['error'] = str(e)
        logger.error(f"{err_msg}:{str(e)}")
        return (err_res, 500)

    try:
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
                res = {
                    "resultCode": "success",
                    "message": "All agencies retrieved successfully.",
                    "data": result
                }
                return (res, 200)
            else:
                res = {
                    "resultCode": "success",
                    "message": "No agencies found.[E002]",
                    "data": []
                }
                return (res, 200)

    except Exception as e:
        # エラーロギング
        logger.error(f"An error occurred: {str(e)}")
        err_msg = 'Error occurred while fetching agencies.'
        detail_err_msg = 'An error occurred while executing the query.'
        err_res['message'] = err_msg
        err_res['data']['error'] = detail_err_msg
        logger.error(f"{err_msg}:{detail_err_msg}")            
        return (err_res, 500)

    finally:
        if 'conn' in locals() and conn.open:
            conn.close()