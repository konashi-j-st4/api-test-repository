from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
import datetime
import json
from response.response_base import create_success_response, create_error_response
from db.db_connection import db

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    elif isinstance(x, datetime.date):
        return x.isoformat()
    elif isinstance(x, datetime.timedelta):
        return x.total_seconds()
    elif isinstance(x, datetime.time):
        return x.isoformat()  
    raise TypeError("Unknown type")

get_powersupplies_router = Blueprint('get_powersupplies', __name__)

@get_powersupplies_router.route('/get_powersupplies', methods=['POST'])
def get_powersupplies():
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'location_id' not in data or 'user_id' not in data:
            return jsonify(create_error_response(
                "location_idとuser_idは必須です",
                None
            )), 400

        location_id = data['location_id']
        app_user_number = data['user_id']
        logger.info(f"Received location_id: {location_id}, app_user_number: {app_user_number}")

        with db.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # app_user_numberからuser_idを取得
                user_id_query = "SELECT user_id FROM m_user WHERE app_user_number = %s"
                cursor.execute(user_id_query, (app_user_number,))
                result = cursor.fetchone()
                if not result:
                    return jsonify(create_error_response(
                        "指定されたapp_user_numberに対応するユーザーが見つかりません",
                        None
                    )), 404
                user_id = result['user_id']
                
                # ユーザー権限の取得
                user_permission_query = "SELECT permission FROM m_user_agency WHERE user_id = %s"
                cursor.execute(user_permission_query, (user_id,))
                user_permission_result = cursor.fetchone()
                
                if not user_permission_result:
                    return jsonify(create_error_response(
                        f"ユーザーID {app_user_number} の権限が見つかりません",
                        None
                    )), 404
                
                user_permission = user_permission_result['permission']
                logger.info(f"ユーザー権限: {user_permission}")

                # 権限リストの生成
                permissions = list(range(1, user_permission + 1))
                
                # 権限とlocation_idのプレースホルダーを作成
                permission_placeholders = ', '.join(['%s'] * len(permissions))
                location_placeholders = ', '.join(['%s'] * len(location_id))

                # メインクエリ
                powersupply_query = f"""
                SELECT powersupply_id,
                        location_id,
                        app_powersupply_number,
                        powersupply_name,
                        plan,
                        type,
                        wat,
                        price,
                        quick_power,
                        nomal_power,
                        maintenance,
                        online,
                        charge_segment,
                        permission,
                        status
                FROM m_powersupply
                WHERE location_id IN ({location_placeholders})
                AND permission IN ({permission_placeholders});
                """
                
                # パラメータの結合
                query_params = location_id + permissions
                
                cursor.execute(powersupply_query, query_params)
                results = cursor.fetchall()
                logger.info("クエリの実行に成功しました")

                # datetime オブジェクトを ISO フォーマットの文字列に変換
                results = json.loads(json.dumps(results, default=datetime_handler))
                
                return jsonify(create_success_response(
                    "充電器情報を取得しました。" if results else "充電器情報が存在しません。[E001]",
                    results if results else None
                )), 200

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "データ取得中にエラーが発生しました",
            str(e)
        )), 500