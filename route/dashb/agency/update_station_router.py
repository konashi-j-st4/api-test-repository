from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
from response.response_base import create_success_response, create_error_response
from db.db_connection import db
from utils.utils import get_jst_now

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

update_station_router = Blueprint('update_station', __name__)

@update_station_router.route('/update_station', methods=['POST'])
def update_station():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'location_id' not in data:
            return jsonify(create_error_response(
                "location_idは必須です",
                None
            )), 400

        # パラメータの取得
        location_id = data['location_id']
        station_name = data.get('station_name')
        zip_code = data.get('zip_code')
        prefecture = data.get('prefecture')
        city = data.get('city')
        address = data.get('address')
        building = data.get('building')
        open_time = data.get('open_time')
        end_time = data.get('end_time')
        open_day = data.get('open_day')
        status = data.get('status', 1)  # デフォルト値1

        logger.info(f"更新パラメータ: station_name={station_name}")

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 現在時刻を取得
                now = get_jst_now()
                
                # 実行クエリ
                update_query = """
                UPDATE m_location
                SET station_name = %s,
                    zip_code = %s,
                    prefecture = %s,
                    city = %s,
                    address = %s,
                    building = %s,
                    open_time = %s,
                    end_time = %s,
                    open_day = %s,
                    status = %s,
                    update_date = %s,
                    update_user = %s
                WHERE location_id = %s;
                """
                cursor.execute(update_query, (
                    station_name, zip_code, prefecture, city,
                    address, building, open_time, end_time,
                    open_day, status, now, 'Dashboard', location_id
                ))

                # 更新された行数を確認
                if cursor.rowcount == 0:
                    return jsonify(create_error_response(
                        "更新対象のデータが見つかりません",
                        None
                    )), 404

                conn.commit()
                logger.info("ステーション情報の更新に成功しました")

                return jsonify(create_success_response(
                    "ステーション情報の更新に成功しました",
                    {
                        "location_id": location_id,
                        "station_name": station_name
                    }
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ更新中にエラーが発生しました",
            str(e)
        )), 500
