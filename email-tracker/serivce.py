import socket
import logging
import json
from datetime import datetime
from db import DatabaseManager

class EmailTracker:

    def __init__(self, port, db_config=None):
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(1)

        logging.basicConfig(filename='/var/log/email_tracker.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

        if db_config:
            self.db_manager = DatabaseManager(**db_config)
        else:
            self.db_manager = None
    

    def handle_request(self, data):
        logging.info(f"Handling data: {data}")

        if "example.com" in data:
            logging.info("Adatok bejöttek, adatbazis kapcsolatot ellenorizzuk")
            if self.db_manager:
                query = "INSERT INTO user_emails (email, last_check, emails_sent_last_minute, total_emails_sent, note_to_admin_sent) VALUES (%(email)s, %(last_check)s,%(emails_sent_last_minute)s,%(total_emails_sent)s,%(note_to_admin_sent)s)"
                params = {
                    'email':"lorinc@almafa.hu",
                    'last_check': datetime.now(), 
                    'emails_sent_last_minute': 3, 
                    'total_emails_sent': 80, 
                    'note_to_admin_sent': datetime.now()
                    }
                self.db_manager.write_data(query, params)
            return "action=DUNNO\n\n"
        else:
            return "action=REJECT\n\n"
    
    
    def run(self):
        logging.info(f"Listening on port {self.port}...")
        try:
            while True:
                conn, addr = self.server_socket.accept()
                logging.info(f"Connected by {addr}")

                try:
                    data = ""
                    
                    while True:
                        chunk = conn.recv(1024)
                    
                        if not chunk:
                            break
                        data += chunk.decode('utf-8')
                    
                        if '\n\n' in data:
                            break
                    
                        if len(data) > 10000: #adatméret korlát ellenőrzése
                            response = "action=REJECT message='Message size exceeds limit'\n\n"
                            conn.sendall(response.encode('utf-8'))
                            conn.close()
                            logging.info(f"Message from {addr} rejected due to size limit")
                        break
                
                    if '\n\n' in data:
                        response = self.handle_request(data)
                        conn.sendall(response.encode('utf-8'))
                        conn.close()
                except Exception as e:
                    logging.error(f"Error processing request from {addr}: {e}")
                    conn.close()
        except Exception as e:
            logging.error(f"An error occured in the server: {e}")
        finally:
            self.server_socket.close()
            logging.info("Server socket closed")

    
if __name__ == '__main__':
    
    with open ('settings/config.json', 'r', encoding='utf-8') as configfile:
        config = json.load(configfile)

    server_port=config['server_port']
    
    db_config = {
        'host': config['db']['host'],
        'user': config['db']['user'],
        'password': config['db']['password'],
        'database': config['db']['database']
    }

    service = EmailTracker(port=server_port, db_config=db_config)
    service.run()