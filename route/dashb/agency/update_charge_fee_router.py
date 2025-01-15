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

update_charge_fee_router = Blueprint('update_charge_fee', __name__)

@update_charge_fee_router.route('/update_charge_fee', methods=['POST'])
def update_charge_fee():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # パラメータの取得と検証
        powersupply_id = data.get('powersupply_id')
        location_id = data.get('location_id')
        price = data.get('price')

        # priceは必須
        if price is None:
            return jsonify(create_error_response(
                "priceは必須です",
                None
            )), 400

        # powersupply_idとlocation_idの両方が取得できた場合はエラー
        if powersupply_id and location_id:
            return jsonify(create_error_response(
                "powersupply_idとlocation_idは同時に指定できません",
                None
            )), 400

        # どちらも取得できなかった場合もエラー
        if not powersupply_id and not location_id:
            return jsonify(create_error_response(
                "powersupply_idまたはlocation_idのいずれかが必要です",
                None
            )), 400

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # 現在時刻を取得
                now = get_jst_now()
                
                # 実行クエリの選択
                if powersupply_id:
                    update_query = """
                    UPDATE m_powersupply
                    SET price = %s,
                        update_date = %s,
                        update_user = %s
                    WHERE powersupply_id = %s;
                    """
                    cursor.execute(update_query, (price, now, 'Dashboard', powersupply_id))
                else:
                    update_query = """
                    UPDATE m_powersupply
                    SET price = %s,
                        update_date = %s,
                        update_user = %s
                    WHERE location_id = %s;
                    """
                    cursor.execute(update_query, (price, now, 'Dashboard', location_id))

                # 更新された行数を確認
                if cursor.rowcount == 0:
                    return jsonify(create_error_response(
                        "更新対象のデータが見つかりません",
                        None
                    )), 404

                conn.commit()
                logger.info("料金情報の更新に成功しました")

                return jsonify(create_success_response(
                    "料金情報の更新に成功しました",
                    {
                        "powersupply_id": powersupply_id,
                        "location_id": location_id,
                        "price": price
                    }
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ更新中にエラーが発生しました",
            str(e)
        )), 500 