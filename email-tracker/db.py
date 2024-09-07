import mysql.connector
from mysql.connector import Error
import logging

class DatabaseManager:
    def __init__(self, host, user, password, database):
        self.connection = None
        try:
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
    
        except Error as e:
            logging.error(f"Error connecting to MySQL database: {e}")

    def read_data(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Failed to read data from Mysql table: {e}")
        finally:
            cursor.close()
    
    def write_data(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            logging.info(f"Query executed successfully: {query}")
        except Error as e:
            self.connection.rollback()
            logging.error(f"Failed to insert data into Mysql Table:{e}")
        finally:
            cursor.close()