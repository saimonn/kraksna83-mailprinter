#!/usr/bin/env python3
import sys
import imaplib
import email
import os
import random
import string
import configparser
import time
import logging
import cups
from pathlib import Path

def find_config():
    candidates = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(Path(xdg) / "mailprinter" / "mailprinter.ini")
        candidates.append(Path(xdg) / "mailprinter.ini")
    candidates.append(Path.home() / ".config" / "mailprinter" / "mailprinter.ini")
    candidates.append(Path.home() / ".config" / "mailprinter.ini")
    candidates.append(Path.home() / ".mailprinter.ini")
    candidates.append(Path("/etc/mailprinter.ini"))
    for p in candidates:
        if p and p.exists():
            return p
    return None

cfg_path = find_config()
if not cfg_path:
    print("No configuration file found (looked in XDG, ~/.config and /etc).", file=sys.stderr)
    sys.exit(2)

config = configparser.ConfigParser()
config.read(cfg_path)

required_options = {
    'IMAP': ['server', 'port', 'username', 'poll_interval', 'password', 'delete_mail'],
    'TEMP': ['directory'],
    'printer': ['printer_name', 'host'],
    'logging': ['level']
}

for section, options in required_options.items():
    if section not in config:
        raise ValueError(f'Missing section: {section} in {cfg_path}')
    for option in options:
        if option not in config[section]:
            raise ValueError(f'Missing option: {option} in section: {section} in {cfg_path}')

log_level = config['logging'].get('level', 'INFO').upper()
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level, logging.INFO))
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
if root_logger.handlers:
    root_logger.handlers = []
root_logger.addHandler(handler)
logging.info(f'Using configuration file: {cfg_path}')

IMAP_SERVER = config['IMAP']['server']
IMAP_PORT = int(config['IMAP'].get('port', '993'))
EMAIL_ACCOUNT = config['IMAP']['username']
POLL_INTERVAL = int(config['IMAP'].get('poll_interval', '60'))
PASSWORD = config['IMAP']['password']
DELETE_MAILS = config['IMAP'].getboolean('delete_mail', fallback=False)

ATTACHMENTS_DIR = Path(config['TEMP']['directory']).expanduser()
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

PRINTER_NAME = config['printer']['printer_name']
PRINTER_HOST = config['printer'].get('host', None)
if PRINTER_HOST:
    try:
        cups.setServer(PRINTER_HOST)
    except Exception as e:
        logging.warning(f'Unable to set CUPS server {PRINTER_HOST}: {e}')

def connect_to_imap():
    try:
        logging.debug(f'Connecting to IMAP {IMAP_SERVER}:{IMAP_PORT} as {EMAIL_ACCOUNT}')
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f'Failed to connect or authenticate to IMAP server: {e}')
        raise

def get_unread_emails(mail):
    try:
        mail.select('INBOX')
        status, response = mail.search(None, 'UNSEEN')
        if status != 'OK':
            logging.debug(f'IMAP search returned non-OK status: {status} {response}')
            return []
        email_ids = response[0].split()
        logging.debug(f'Found {len(email_ids)} unread messages')
        return email_ids
    except Exception as e:
        logging.error(f'Error while searching mailbox: {e}')
        return []

def download_attachments(mail, email_ids):
    for e_id in email_ids:
        try:
            status, response = mail.fetch(e_id, '(RFC822)')
            if status != 'OK' or not response or not response[0]:
                logging.debug(f'Failed to fetch email id {e_id}: {status} {response}')
                continue
            msg = email.message_from_bytes(response[0][1])
            subj = msg.get("Subject", "(no subject)")
            logging.info(f'Email subject: {subj}')
            keyword = config['IMAP'].get('keyword', None)
            if keyword and keyword not in subj:
                logging.info(f'Keyword "{keyword}" missing in subject, skipping message')
                continue
            for index, part in enumerate(msg.walk()):
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    suffix = Path(filename).suffix
                    base = Path(filename).stem
                else:
                    suffix = '.pdf'
                    base = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                filepath = ATTACHMENTS_DIR / f"{base}_{random_string}_{index}{suffix}"
                with open(filepath, 'wb') as f:
                    payload = part.get_payload(decode=True)
                    if payload:
                        f.write(payload)
                    else:
                        logging.debug('No payload for part, skipping')
                        continue
                logging.info(f'Downloaded attachment to {filepath}')
                return str(filepath)
        except Exception as e:
            logging.error(f'Error processing email {e_id}: {e}')
    return None

def delete_all_emails(mail):
    try:
        mail.select('INBOX')
        status, response = mail.search(None, 'ALL')
        if status != 'OK':
            logging.debug(f'IMAP search ALL returned {status}')
            return
        email_ids = response[0].split()
        for e_id in email_ids:
            mail.store(e_id, '+FLAGS', '\\Deleted')
        mail.expunge()
        logging.info('Deleted all emails from INBOX')
    except Exception as e:
        logging.error(f'Error deleting emails: {e}')

def print_pdf(filepath):
    try:
        logging.info(f'Printing PDF {filepath} to printer {PRINTER_NAME}')
        conn = cups.Connection()
        printers = conn.getPrinters()
        if PRINTER_NAME not in printers:
            logging.error(f'Printer "{PRINTER_NAME}" not found on CUPS server')
            return False
        if not str(filepath).lower().endswith('.pdf'):
            logging.error('File is not a PDF, skipping print')
            return False
        conn.printFile(PRINTER_NAME, filepath, "MailPrinter Job", {})
        logging.info('Print job submitted')
        return True
    except Exception as e:
        logging.error(f'Failed to print {filepath}: {e}')
        return False

def list_resources():
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
        print('Available printers:')
        for p in printers:
            print(p)
    except Exception as e:
        print(f'Failed to list printers: {e}', file=sys.stderr)
    try:
        mail = connect_to_imap()
        print('Available mailboxes:')
        print(mail.list())
        mail.logout()
    except Exception as e:
        print(f'Failed to list mailboxes: {e}', file=sys.stderr)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_resources()
        return
    while True:
        mail = None
        try:
            mail = connect_to_imap()
            email_ids = get_unread_emails(mail)
            if not email_ids:
                logging.debug('No unread emails found')
            fpath = download_attachments(mail, email_ids)
            if fpath:
                ok = print_pdf(fpath)
                try:
                    os.remove(fpath)
                    logging.debug(f'Removed temporary file {fpath}')
                except Exception as e:
                    logging.warning(f'Could not remove {fpath}: {e}')
            if DELETE_MAILS:
                logging.debug('Configured to delete mails; deleting all.')
                delete_all_emails(mail)
        except Exception as e:
            logging.error(f'Unhandled error in main loop: {e}')
        finally:
            try:
                if mail:
                    mail.logout()
            except Exception:
                pass
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

