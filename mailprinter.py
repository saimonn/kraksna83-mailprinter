#!/usr/bin/env python3
import sys
import imaplib
import email
import os
import random
import string
import configparser
import time
import cups # PyCUPS

# Read configuration from file
config = configparser.ConfigParser()
if os.path.isfile('config.ini') :
    config.read('config.ini')
else:
    config.read('/etc/mailprinter.ini')
# Check if all required options are present
required_options = {
    'IMAP': ['server', 'port', 'username', 'poll_interval', 'password', 'delete_mail'],
    'TEMP': ['directory'],
    'printer': ['printer_name', 'host'],
    'logging': ['level', 'filename']
}

for section, options in required_options.items():
    if section not in config:
        raise ValueError(f'Missing section: {section}')
    for option in options:
        if option not in config[section]:
            raise ValueError(f'Missing option: {option} in section: {section}')

if 'logging' in config:
    import logging
    if config['logging']['level'] == 'DEBUG':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(filename=config['logging']['filename'], level=logging.INFO)
    logging.info('Starting mailprinter.py')


# IMAP server credentials
IMAP_SERVER = config['IMAP']['server']
IMAP_PORT = config['IMAP']['port']
EMAIL_ACCOUNT = config['IMAP']['username']
POLL_INTERVAL = int(config['IMAP']['poll_interval'])
PASSWORD = config['IMAP']['password']
DELETE_MAILS=config['IMAP']['delete_mail']

# Directory to save attachments
ATTACHMENTS_DIR = config['TEMP']['directory']

# Printer name
PRINTER_NAME = config['printer']['printer_name']
PRINTER_HOST = config['printer']['host']
cups.setServer(PRINTER_HOST)


def connect_to_imap():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f'Failed to connect to IMAP server: {e}')
        raise

def get_unread_emails(mail):
    #list mailboxes 
    logging.debug(mail.list())
    mail.select('inbox')
    status, response = mail.search(None, 'UNSEEN')
    email_ids = response[0].split()
    return email_ids

def download_attachments(mail, email_ids):
    if not os.path.exists(ATTACHMENTS_DIR):
        os.makedirs(ATTACHMENTS_DIR)

    for e_id in email_ids:

        status, response = mail.fetch(e_id, '(RFC822)')
        email_message = email.message_from_bytes(response[0][1])
        #print email subject
        logging.info(f'Email subject: {email_message["Subject"]}')
        if 'keyword' in config['IMAP'] and config['IMAP']['keyword'] not in email_message["Subject"]:
            logging.info(f'Keyword {config["IMAP"]["keyword"]} missing in email subject, ignoring')
            continue  # Continue to the next email

        for index, part in enumerate(email_message.walk()):
            #print (part)
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                random_string= ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                filepath = os.path.join(ATTACHMENTS_DIR, f"{random_string}_{index}.pdf")
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                logging.info(f'Downloaded {filename}')
                return filepath
    return None  # Return None if no attachments were downloaded


def delete_all_emails(mail):
    mail.select('inbox')
    status, response = mail.search(None, 'ALL')
    email_ids = response[0].split()
    for e_id in email_ids:
        mail.store(e_id, '+FLAGS', '\\Deleted')
    mail.expunge()
    logging.info('All emails have been deleted.')


def print_pdf(filepath):

    logging.info('Printing PDF document...')

    conn = cups.Connection()
    printers = conn.getPrinters()
    #check if printer is available
    if PRINTER_NAME not in printers:
        logging.error(f'Printer {PRINTER_NAME} not found on server {PRINTER_HOST}')
        return
    if not filepath.endswith('.pdf'):
        logging.error('The file is not a PDF document.')
        return
    logging.info(f'Sending {filepath} to printer {PRINTER_NAME}')
    conn.printFile(PRINTER_NAME, filepath, "Print Job", {})


def main():
    mail = connect_to_imap()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            # List available printers
            print('Available printers:')
            conn = cups.Connection()
            printers = conn.getPrinters()
            for printer in printers:
                print(printer)
            #list available mailboxes
            mailboxes = mail.list()
            print(f'Available mailboxes: {mailboxes}')
            quit()
            


    while True:
        try:
            mail = connect_to_imap()
            logging.debug('Checking for new emails...')
            email_ids = get_unread_emails(mail)
            fpath = download_attachments(mail, email_ids)
            if fpath:
                logging.debug(f'Printing {fpath}')
                print_pdf(fpath)
                logging.debug(f'Deleting {fpath}')
                os.remove(fpath)

            if DELETE_MAILS:
                logging.debug('Deleting all emails.')
                delete_all_emails(mail)
        except Exception as e:
            logging.error(f'An error occurred: {e}')
        finally:
            mail.logout()
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
