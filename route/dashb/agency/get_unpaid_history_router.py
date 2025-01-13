from flask import Blueprint, jsonify, request
import logging
import pymysql
import os
from response.response_base import create_success_response, create_error_response

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

get_unpaid_history_router = Blueprint('get_unpaid_history', __name__)

@get_unpaid_history_router.route('/get_unpaid_history', methods=['POST'])
def get_unpaid_history():
    conn = None
    try:
        # リクエストボディから情報を取得
        data = request.get_json()
        if not data:
            return jsonify(create_error_response(
                "リクエストボディが空です",
                None
            )), 400

        # 必須パラメータの確認
        if 'user_id' not in data:
            return jsonify(create_error_response(
                "user_idは必須です",
                None
            )), 400

        user_id = data['user_id']
        logger.info(f"Received user_id: {user_id}")

        # MySQLに接続
        conn = pymysql.connect(
            host=os.environ['END_POINT'],
            user=os.environ['USER_NAME'],
            passwd=os.environ['PASSWORD'],
            db=os.environ['DB_NAME'],
            port=int(os.environ['PORT']),
            connect_timeout=60
        )
        logger.info("データベースへの接続に成功しました")

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # ユーザーの権限レベルを取得
                permission_query = """
                SELECT a.permission, a.agency_id
                FROM m_user_agency a
                WHERE a.user_id = %s
                """
                cursor.execute(permission_query, (user_id,))
                permission_result = cursor.fetchone()
                
                if not permission_result:
                    return jsonify(create_error_response(
                        f"ユーザーID {user_id} の権限が見つかりません",
                        None
                    )), 404
                
                user_permission = permission_result['permission']
                agency_id = permission_result['agency_id']
                permissions = list(range(1, user_permission + 1))
                permission_placeholders = ', '.join(['%s'] * len(permissions))

                # 権限とagency_idに基づいてpowersupply_idを取得
                powersupply_query = f"""
                SELECT DISTINCT p.powersupply_id
                FROM m_powersupply p
                JOIN m_location l ON p.location_id = l.location_id
                WHERE l.agency_id = %s
                AND p.permission IN ({permission_placeholders})
                """
                cursor.execute(powersupply_query, (agency_id,) + tuple(permissions))
                powersupply_results = cursor.fetchall()
                
                if not powersupply_results:
                    return jsonify(create_success_response(
                        "未払い取引が存在しません。[E001]",
                        None
                    )), 200

                powersupply_ids = [item['powersupply_id'] for item in powersupply_results]
                placeholders = ', '.join(['%s'] * len(powersupply_ids))
                logger.info(f"対象の充電器ID: {powersupply_ids}")

                # 未払い取引を取得
                unpaid_query = f"""
                SELECT 
                    t.transaction_id,
                    l.station_name,
                    ps.app_powersupply_number,
                    h.charging_start,
                    h.charging_time,
                    h.charging_rate,
                    h.charged_amount,
                    h.billing_amount,
                    u.app_user_number,
                    u.lastname,
                    u.firstname
                FROM t_charge t
                JOIN t_charge_payment p ON t.transaction_id = p.transaction_id
                JOIN t_charge_history h ON t.transaction_id = h.transaction_id
                JOIN m_powersupply ps ON t.powersupply_id = ps.powersupply_id
                JOIN m_location l ON ps.location_id = l.location_id
                JOIN m_user u ON t.user_id = u.user_id
                WHERE t.powersupply_id IN ({placeholders})
                AND p.payment_status = 0
                ORDER BY h.charging_start DESC
                """
                
                cursor.execute(unpaid_query, tuple(powersupply_ids))
                results = cursor.fetchall()
                logger.info("クエリの実行に成功しました")
                
                # datetimeオブジェクトを文字列に変換
                for record in results:
                    record['charging_start'] = record['charging_start'].isoformat() if record['charging_start'] else None

                return jsonify(create_success_response(
                    "未払い取引を取得しました。" if results else "未払い取引が存在しません。[E001]",
                    results if results else None
                )), 200

        except Exception as e:
            logger.error(f"クエリ実行中にエラーが発生しました: {str(e)}")
            return jsonify(create_error_response(
                "クエリ実行中にエラーが発生しました",
                str(e)
            )), 500

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return jsonify(create_error_response(
            "パラメータまたは環境変数の取得に失敗しました",
            str(e)
        )), 500

    finally:
        if conn and conn.open:
            conn.close()
            logger.info("データベース接続を終了しました")