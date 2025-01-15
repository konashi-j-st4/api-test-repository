"""
Phone number utility functions for formatting and validation.
"""
import re
import logging
import hmac
import base64
import hashlib
import datetime
import pytz

# ロガー設定
logger = logging.getLogger(__name__)

def get_jst_now():
    """
    現在の日本時間を取得します。

    Returns:
        str: 日本時間（YYYY-MM-DD HH:MM:SS形式）
    """
    jst = pytz.timezone('Asia/Tokyo')
    return datetime.datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')

def format_phone_number(phone):
    """
    電話番号を国際形式（E.164）に変換します。

    Args:
        phone (str): フォーマットする電話番号

    Returns:
        str: E.164形式の電話番号（例：+819012345678）

    Raises:
        ValueError: 電話番号のフォーマットが不正な場合
    """

    # 数字以外の文字を削除
    digits_only = re.sub(r'\D', '', phone)
    
    # 日本の電話番号を想定
    if digits_only.startswith('0'):
        formatted = '+81' + digits_only[1:]
    elif digits_only.startswith('81'):
        formatted = '+' + digits_only
    else:
        formatted = '+81' + digits_only

    # E.164 形式の検証
    if not re.match(r'^\+81[1-9]\d{9}$', formatted):
        error_msg = f"電話番号のフォーマットが不正です: {formatted}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"電話番号のフォーマットが成功しました")
    return formatted 

def calculate_secret_hash(username, client_id, client_secret):
    """
    AWS Cognitoの認証に必要なシークレットハッシュを計算します。

    Args:
        username (str): ユーザー名（通常は電話番号）
        client_id (str): CognitoクライアントID
        client_secret (str): Cognitoクライアントシークレット

    Returns:
        str: 計算されたシークレットハッシュ（Base64エンコード済み）
    """
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), 
                   msg=message.encode('utf-8'), 
                   digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode() 