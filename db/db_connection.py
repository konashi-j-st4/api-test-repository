import os
import logging
import pymysql
from contextlib import contextmanager

# logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DBConnection:
    def __init__(self):
        self.host = os.environ['END_POINT']
        self.user = os.environ['USER_NAME']
        self.password = os.environ['PASSWORD']
        self.db = os.environ['DB_NAME']
        self.port = int(os.environ['PORT'])

    def connect(self):
        """データベース接続を作成する"""
        try:
            connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                port=self.port,
                connect_timeout=60
            )
            logger.info("データベースへの接続に成功しました")
            return connection
        except Exception as e:
            logger.error(f"データベース接続中にエラーが発生しました: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """コンテキストマネージャーとしてデータベース接続を提供する"""
        conn = None
        try:
            conn = self.connect()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.info("データベース接続を終了しました")

# シングルトンインスタンスを作成
db = DBConnection()