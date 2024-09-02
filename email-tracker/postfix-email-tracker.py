import sys
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import logging

try:
    # Log fájl beállítása és a logging konfigurációja
    logging.basicConfig(filename='/var/log/postfix_policy_service.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    db = mysql.connector.connect(
        host="localhost",
        user="your_username",
        passwd="your_password",
        database="email_tracker"
    )
    cur = db.cursor()
except Error as e:
    sys.stderr.write("Database connection failed: " + str(e) + "\n")
    sys.exit(1)

def send_alert_email(sender):
    admin_email = "admin@example.com"
    try:
        with smtplib.SMTP('localhost') as server:
            msg = MIMEText(f'The sender {sender} has exceeded the email sending limit.')
            msg['Subject'] = 'Alert: Email limit exceeded'
            msg['From'] = admin_email
            msg['To'] = admin_email
            server.sendmail(admin_email, [admin_email], msg.as_string())
    except Exception as e:
        sys.stderr.write("Failed to send email: " + str(e) + "\n")

def is_whitelisted(email):
    try:
        cur.execute("SELECT email FROM whitelist WHERE email = %s", (email,))
        return cur.fetchone() is not None
    except Error as e:
        sys.stderr.write("Failed to check whitelist: " + str(e) + "\n")
        return False

def check_limit(sender):
    if is_whitelisted(sender):
        logging.info(f"Sender {sender} is whitelisted. No limit check required.")
        return "action=OK\n\n"
    
    try:
        current_time = datetime.now()
        cur.execute("SELECT last_check, emails_sent_last_minute, total_emails_sent FROM user_emails WHERE email = %s", (sender,))
        row = cur.fetchone()

        if row:
            last_check, emails_sent_last_minute, total_emails_sent = row
            if current_time - last_check > timedelta(minutes=1):
                emails_sent_last_minute = 0
            
            logging.info(f"Sender {sender} is whitelisted. No limit check required.")
        else:
            logging.info(f"Sender {sender} is whitelisted. No limit check required.")
            last_check = current_time
            emails_sent_last_minute = 0
            total_emails_sent = 0
            cur.execute("INSERT INTO user_emails (email, last_check, emails_sent_last_minute, total_emails_sent) VALUES (%s, %s, %s, %s)",
                        (sender, last_check, emails_sent_last_minute, total_emails_sent))
            db.commit()

        if emails_sent_last_minute < 3:
            emails_sent_last_minute += 1
            total_emails_sent += 1
            cur.execute("UPDATE user_emails SET last_check = %s, emails_sent_last_minute = %s, total_emails_sent = %s WHERE email = %s",
                        (current_time, emails_sent_last_minute, total_emails_sent, sender))
            db.commit()
            return "action=OK\n\n"
        else:
            send_alert_email(sender)
            return "action=DUNNO 450 Too many emails, please try again later.\n\n"
        
    except Error as e:
        logging.error(f"Database operation failed for sender {sender}: {e}")
        sys.stderr.write("Database operation failed: " + str(e) + "\n")
        return "action=DUNNO 450 Server error, please try again later.\n\n"

while True:
    line = sys.stdin.readline().strip()
    if line == '':
        break
    if line.startswith("sender="):
        sender = line.split('=')[1]
        response = check_limit(sender)
        sys.stdout.write(response)
        sys.stdout.flush()

cur.close()
db.close()