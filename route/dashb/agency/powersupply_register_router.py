from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.db_utils import generate_unique_number

# ロガー設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

powersupply_register_router = Blueprint('powersupply_register', __name__)

@powersupply_register_router.route('/powersupply_register', methods=['POST'])
def powersupply_register():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        required_fields = [
            'location_id', 'powersupply_name', 'type', 'wat', 'price',
            'quick_power', 'nomal_power', 'maintenance', 'online',
            'charge_segment', 'permission'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_error_response(
                f"必須パラメータが不足しています: {', '.join(missing_fields)}",
                None
            )), 400

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 現在時刻を取得
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # ユニークな12桁の数字を生成
                try:
                    app_powersupply_number = generate_unique_number(cursor, 'm_powersupply', 'app_powersupply_number', 12)
                except ValueError as e:
                    return jsonify(create_error_response(
                        str(e),
                        None
                    )), 500
                
                # 実行クエリ
                insert_query = """
                INSERT INTO m_powersupply (
                    location_id, app_powersupply_number, powersupply_name,
                    type, wat, price, quick_power, nomal_power,
                    maintenance, online, charge_segment, permission,
                    create_date, create_user, update_date, update_user, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                );
                """
                cursor.execute(insert_query, (
                    data['location_id'], app_powersupply_number, data['powersupply_name'],
                    data['type'], data['wat'], data['price'], data['quick_power'],
                    data['nomal_power'], data['maintenance'], data['online'],
                    data['charge_segment'], data['permission'],
                    now, 'Dashboard', now, 'Dashboard', 1
                ))
                conn.commit()
                
                logger.info("充電器情報の登録に成功しました")
                return jsonify(create_success_response(
                    "充電器情報の登録に成功しました",
                    {"app_powersupply_number": app_powersupply_number}
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ登録中にエラーが発生しました",
            str(e)
        )), 500 