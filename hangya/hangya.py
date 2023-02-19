#!/usr/bin/python3

""" Module helping the syncronization between webserver and proxy server"""
import logging
import os
import json
import subprocess
import socket
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import inspect
import mysql.connector
from mysql.connector import errorcode
from jinja2 import Environment, FileSystemLoader


##############################################################
################### LOGGER SETUP #############################
##############################################################

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file_handler = logging.FileHandler('/var/log/hangya.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


##############################################################
################### EMAIL KÜLDÉS #############################
##############################################################

class Email:
  """Class for sending emails"""

  def __init__(self, config):
    self._host = config["host"]
    self._port = config["port"]
    self._username = config["username"]
    self._password = config["password"]
    self._receiver = config["receiver"]
    self._sendername = config["sender"]
    self._ehlo = config["ehlo"]

  @property
  def email_from(self):
    """Setting name to email address for the sender"""
    return f"{self._sendername} <{self._username}>"

  def send(self, subject, text="", text_html=""):
    """Sending email messages"""
    if text == "" and text_html == "":
      logger.error("Üres üzenetet nem fogok kiküldeni emailen! Ez spammelés!")
    else:
      message = MIMEMultipart("alternative")
      message["Subject"] = subject
      message["From"] = self.email_from
      message["To"] = self._receiver

      if text != "":
        part1 = MIMEText(text, "plain")
        message.attach(part1)

      if text_html != "":
        part2 = MIMEText(text_html, "plain")
        message.attach(part2)
      try:
        smtp = smtplib.SMTP(self._host, port=self._port, timeout=10)

        smtp.ehlo(self._ehlo)

        smtp.starttls()

        smtp.login(self._username, self._password)

        smtp.sendmail(self._username, self._receiver, message.as_string())

        smtp.quit()
      except smtplib.SMTPException as err:
        logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err )

##############################################################
################### WEBSITECONFIG ############################
##############################################################

class WebsiteConfig:
  """This class is for managing nginx configuration files"""

  error = []
  restart_needed = False

  def __init__ (self, database_config, nginx_config):
    self._database_config = database_config
    self._nginx_config = nginx_config

  @property
  def sites_available(self):
    """Gives back the path of available sites"""

    return f"{self._nginx_config['config_directory']}/sites-available"

  @property
  def sites_enabled(self):
    """Gives back the path of enabled sites"""

    return f"{self._nginx_config['config_directory']}/sites-enabled"

  def manage_all_nginx_config(self):
    """This function is responsible for managing the config file creation/deletion"""

    try:
      mysql_fields = ['domain', 'active', 'ssl', 'ssl_letsencrypt', 'is_subdomainwww']
      mysql_table = "web_domain"

      all_existing_websites = self.query_database(mysql_fields, mysql_table)

      if not all_existing_websites:
        raise ValueError("Az adatok lekérdezése az adatbázisból nem sikerült.")

      for website_data in all_existing_websites:

        domain = website_data[0]
        active = website_data[1]
        ssl = website_data[2]
        ssl_letsencrypt = website_data[3]
        is_subdomainwww = website_data[4]

        destination_ip = self._database_config["host"]

        self.one_nginx_config(active, is_subdomainwww, destination_ip, ssl, ssl_letsencrypt, domain)

      return True
    except ValueError as err:
      logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err )
      self.error.append(repr(err))
      return False

  def one_nginx_config(self, active, is_subdomainwww, destination_ip, ssl, ssl_letsencrypt, domain):
    """This function takes care of one nginx config"""

    try:
      sites_enabled_config = f"{self.sites_enabled}/{domain}.conf"

      if active == 'y':

        if not os.path.isfile(sites_enabled_config):

          if self.write_nginx_config(domain, destination_ip, ssl,
              ssl_letsencrypt, is_subdomainwww):

            self.restart_needed = True

          else:
            raise ValueError(f"{sites_enabled_config} fájl létrehozása nem sikerült")

        else:

          current_config = self.read_nginx_config(domain)

          if not current_config:
            raise ValueError(
              f"Meglévő konfig fájlt kellett volna beolvasni, de nem sikerült."
              f"Ennek a hibának nem is szabadna előfordulnia\n {sites_enabled_config}"
              )

          current_config_ssl = re.search("listen 443 ssl;", current_config)

          if (current_config_ssl and ssl == 'n') or \
             (not current_config_ssl and ssl== 'y'):

            if not self.delete_nginx_config(domain) or \
               not self.write_nginx_config(domain,destination_ip,ssl,
                  ssl_letsencrypt, is_subdomainwww):

              raise ValueError(f"A {domain} újrakonfigurálása (törlés/létrehozás) \
                  nem járt sikerrel!")

            self.restart_needed = True

      elif active == 'n':

        if os.path.isfile(sites_enabled_config):

          if self.delete_nginx_config(domain):
            self.restart_needed = True
          else:
            raise ValueError(f"{sites_enabled_config} fájl törlése nem sikerült.")

      return True

    except ValueError as err:
      logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err )
      self.error.append(repr(err))
      return False

  def query_database(self, fields, table):
    """This reads data from mysql database"""

    try:

      username = self._database_config["username"]
      password = self._database_config["password"]
      host = self._database_config["host"]
      name = self._database_config["name"]

      mysql_conn = mysql.connector.connect(
        user=username,
        password=password,
        host=host,
        database=name
        )

      mysql_query = f"select `{'`,`'.join(fields)}` from {table}"

      mysql_cursor = mysql_conn.cursor()
      mysql_cursor.execute(mysql_query)

      mysql_data = mysql_cursor.fetchall()
      mysql_conn.close()
      return mysql_data

    except mysql.connector.Error as err:

      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        logger.error('%s/%s: Felhasználó név vagy jelszó nem megfelelő', \
          __class__.__name__, inspect.stack()[0][3] )
        self.error.append("Felhasználó név vagy jelszó nem megfelelő!")

      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        logger.error('%s/%s: A megadott adatbázis nem létezik', \
          __class__.__name__, inspect.stack()[0][3] )
        self.error.append("A megadott adatbázis nem létezik")

      else:
        logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err.msg )
        self.error.append(err.msg)

      mysql_data = False
      return mysql_data


  def write_nginx_config(self, domain, destination_ip, ssl, ssl_letsencrypt, is_subdomainwww):
    """This writes an nginx config file"""

    try:
      domain_url = f"{domain} www.{domain}" if (is_subdomainwww==1) else domain
      environment = Environment(loader=FileSystemLoader("templates/"))
      template = environment.get_template("nginx.j2")
      content = template.render(
              domain_url = domain_url,
              destination_ip = destination_ip,
              ssl = ssl,
              ssl_letsencrypt = ssl_letsencrypt,
              cert_directory = self._nginx_config["cert_directory"],
              domain = domain
            )

      sites_available_config = f"{self.sites_available}/{domain}.conf"
      sites_enabled_config = f"{self.sites_enabled}/{domain}.conf"

      with open(sites_available_config, mode="w", encoding="utf-8") as nginx_config:
        nginx_config.write(content)

      os.symlink(sites_available_config, sites_enabled_config)

      return True

    except Exception as err:
      logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err )
      self.error.append(repr(err))
      return False

  def delete_nginx_config(self, domain):
    """This deletes an existing nginx config file"""

    try:
      sites_enabled_config = f"{self.sites_enabled}/{domain}.conf"
      sites_available_config=f"{self.sites_available}/{domain}.conf"

      if os.path.isfile(sites_enabled_config):
        os.unlink(sites_enabled_config)

      if os.path.isfile(sites_available_config):
        os.unlink(sites_available_config)

      return True

    except Exception as err:
      logger.error('%s/%s:%s', __class__.__name__, inspect.stack()[0][3], err )
      self.error.append(repr(err))
      return False

  def read_nginx_config(self, domain):
    """This reads an exisiting nginx config file for further checks"""

    sites_enabled_config = f"{self.sites_enabled}/{domain}.conf"
    if os.path.isfile(sites_enabled_config):
      with open (sites_enabled_config, mode="r", encoding="utf-8") as config:
        return config.read()
    else:
      self.error.append(f"A megadott config fájl nem létezik ({sites_enabled_config}) ")
      return False



##############################################################
################### MAIN #####################################
##############################################################
def main():
  """This is the main function of the module"""

  config_file = "config.json"

  if not os.path.isfile(config_file):
    logger.error('%s nem található, a szükséges konfigurációt nem tudom betölteni...', config_file)

  else:

    with open(config_file, "r", encoding="utf-8") as con:
      config = json.load(con)

    webconfig = WebsiteConfig(config["database"], config["nginx"])

    try:

      if not webconfig.manage_all_nginx_config():
        raise ValueError("A websiteok configurálása nem sikerült")


      if webconfig.restart_needed:
        nginx_config_test = subprocess.getoutput(['nginx -t'])

        if re.search('error',nginx_config_test, re.IGNORECASE) or \
          re.search('failed',nginx_config_test, re.IGNORECASE):

          raise ValueError(f"Az nginx config testje nem sikerült:\n{nginx_config_test}")

        subprocess.run(["nginx", "-s", "reload"], check=True)

    except ValueError as err:
      logger.error('%s:%s',inspect.stack()[0][3], err )
      error_text = webconfig.error
      error_text.append(repr(err))
      email = Email(config["smtp"])
      email.send("Sikertelen weblap szinkronizáció", create_email_message(error_text), "")

def create_email_message(error):
  """This function creates the email message body based on the website class error object"""
  error_message = "\n".join(reversed(error))

  message = (
    f"Dátum: {datetime.datetime.now()}\n"
    f"Gép: {socket.gethostname()}\n"
    f"===============================================================\n\n"
    f"A weblapok szinkronizálása nem sikerült az alábbi okok miatt:\n"
    f"{error_message}\n"
    f"===============================================================\n\n"
    f"Kérlek, nézz utána a logokban is, hogy mi lehetett a probléma! "
  )
  return message

if __name__ == '__main__':
  main()
