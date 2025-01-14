from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

qr_powersupply_info_router = Blueprint('qr_powersupply_info', __name__)

@qr_powersupply_info_router.route('/qr_powersupply_info', methods=['POST'])
def qr_powersupply_info():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'app_powersupply_number' not in data:
            return jsonify(create_error_response(
                "app_powersupply_numberは必須です",
                None
            )), 400

        app_powersupply_number = data['app_powersupply_number']
        logger.info(f"Received app_powersupply_number: {app_powersupply_number}")

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 必要な情報のみを取得するクエリ
                powersupply_query = """
                SELECT app_powersupply_number, powersupply_name
                FROM m_powersupply
                WHERE app_powersupply_number = %s;
                """
                
                cursor.execute(powersupply_query, (app_powersupply_number,))
                result = cursor.fetchone()
                logger.info("クエリの実行に成功しました")

                if result:
                    return jsonify(create_success_response(
                        "充電器情報を取得しました。",
                        result
                    )), 200
                else:
                    return jsonify(create_success_response(
                        "充電器情報が存在しません。[E001]",
                        None
                    )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500