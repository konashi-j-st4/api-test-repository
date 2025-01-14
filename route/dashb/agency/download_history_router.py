from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

download_history_router = Blueprint('download_history', __name__)

@download_history_router.route('/download_history', methods=['POST'])
def download_history():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400
        
        location_id = data.get('location_id')
        powersupply_id = data.get('powersupply_id')

        if not location_id and not powersupply_id:
            return jsonify(create_error_response(
                "location_id または powersupply_id は必須です",
                None
            )), 400

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                query = """
                SELECT
                    t_charge.transaction_id,
                    t_charge_history.charging_start,
                    t_charge_history.charging_end,
                    t_charge_history.charged_amount,
                    t_charge_history.billing_amount,
                    m_user.app_user_number,
                    m_location.station_name,
                    m_powersupply.app_powersupply_number,
                    m_powersupply.powersupply_name
                FROM
                    t_charge
                JOIN t_charge_history ON t_charge.transaction_id = t_charge_history.transaction_id
                JOIN m_user ON t_charge.user_id = m_user.user_id
                JOIN m_powersupply ON t_charge.powersupply_id = m_powersupply.powersupply_id
                JOIN m_location ON m_powersupply.location_id = m_location.location_id
                WHERE {condition} = %s
                ORDER BY t_charge_history.charging_start DESC;
                """.format(condition = 'm_location.location_id' if location_id else 't_charge.powersupply_id')
                
                cursor.execute(query, (location_id or powersupply_id,))
                result = cursor.fetchall()
                logger.info("クエリの実行に成功しました")

                # datetimeオブジェクトを文字列に変換
                for record in result:
                    record['charging_start'] = record['charging_start'].isoformat() if record['charging_start'] else None
                    record['charging_end'] = record['charging_end'].isoformat() if record['charging_end'] else None

                return jsonify(create_success_response(
                    "データを取得しました。" if result else "データが存在しません。",
                    result
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500 