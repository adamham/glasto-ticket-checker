#!/usr/bin/env python
"""

A python script born from a need to check the Glastonbury ticket site incredibly often, in the vain hope
that if and when extra tickets go on sale, someone (let's say 'a friend' who forgot to pay for their ticket in time)
can get a notification so they can try and grab one. Allegedly these tickets appear randomly and disappear very
quickly, so, automation is needed.

A Dockerfile can be used to build an image that will run this. Once built run it with something like:
docker run -e "LOG_DEBUG=yes" -e "EMAIL_NOTIFICATIONS=yes" -e "SMS_NOTIFICATIONS=yes" --restart always \
--name foo <image>

It can be run as a regular script as well:

./ticket-checker.py -sms -email -debug -log /tmp/foo

The following environment variables are needed. Either add them to the Dockerfile, add them running the containers,
or export them prior to running the script manually.

Mandatory:

POLLING_INTERVAL - How often to check the site
TICKET_URL - the url to scrape
LOG_DEBUG - yes/no flag
EMAIL_NOTIFICATIONS - email notifications on/off
SMS_NOTIFICATIONS - sms notifications on/off

Optional:

SMTP_FROMADDR - your email address
SMTP_TOADDRS - comma separated string of email addresses 'email1, email2'
SMTP_GMAIL_USERNAME - your gmail username
SMTP_GMAIL_PASSWORD - your gmail password

TWILIO_ACCTSID - your Twilio account SID
TWILIO_ACCTTOKEN - your Twilio account token
TWILIO_NUMBER - your Twilio number
SMS_TOADDRS = comma separated string of phone numbers 'number1, number2'

"""
# TODO: logging isn't very good

import requests
import difflib
import time
import io
import smtplib
import logging
import argparse
import os
from twilio.rest import TwilioRestClient
from twilio import TwilioRestException
from bs4 import BeautifulSoup
from ghost import Ghost
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from time import strftime


def send_email(current_time, url):
    """
    Send a notification email to our list with a screen grab of the ticket page that has changed.

    :param current_time: The time a change was detected
    :parm url: Ticket page URL
    :return:
    """

    logger = logging.getLogger('ticket-checker')
    logger.debug('Setting up mail')

    fromaddr = os.environ['SMTP_FROMADDR']
    toaddrs = os.environ['SMTP_TOADDRS']
    recipients = list(toaddrs.replace(' ','').split(','))
    username = os.environ['SMTP_GMAIL_USERNAME']
    password = str(os.environ['SMTP_GMAIL_PASSWORD']).replace('\\','') #urgh (env vars don't like special chars in pwd)

    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddrs
    msg['Subject'] = "Glastonbury ticket site updated!"

    body = "Changes have been made to the Glastonbury ticket website!\n\n%s\n\nPage image attached.\n \
        Change detected at %s\n\n\n" % (url, current_time)
    msg.attach(MIMEText(body, 'plain'))

    filename = "tickets_page.png"
    attachment = open("./tickets_page.png", "rb")

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    msg.attach(part)

    logger.debug('Sending mail to %s', toaddrs)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(username, password)
        text = msg.as_string()
        server.sendmail(fromaddr, recipients, text)
        server.quit()
        logger.debug('Mail sent')
    except smtplib.SMTPException as e:
        logger.info(e)


class MessageClient(object):
    def __init__(self):
        self.twilio_number = os.environ['TWILIO_NUMBER']
        self.twilio_client = TwilioRestClient(os.environ['TWILIO_ACCTSID'], os.environ['TWILIO_ACCTTOKEN'])

    def send_message(self, body, to):
        self.twilio_client.messages.create(body=body, to=to, from_=self.twilio_number)


def send_sms(current_time, url):
    """
    Send SMS messages to our SMS recipients notifying them of a change.

    :param current_time: The time a change was detected
    :parm url: Ticket page URL
    :return:
    """
    logger = logging.getLogger('ticket-checker')
    logger.debug('Sending SMS notifications')

    twilio_client = MessageClient()

    try:
        for phone in os.environ['SMS_TOADDRS'].split(','):
            twilio_client.send_message\
                ("The Glasto ticket page has been updated. Checked: %s\n%s" % (current_time, url), phone.strip())
    except TwilioRestException as e:
        logger.info("SMS notification error: %s" % e)


def check_ticket_site(smtp_notify=False, sms_notify=False):
    """
    Run indefinitely.
    Check the ticket site.
    If it changes, send some sort of notification
    :param smtp_notify: flag
    :param sms_notify: flag
    :return:
    """

    current_page = ''
    check_count = 1
    url = os.environ['TICKET_URL']
    polling_interval = int(os.environ['POLLING_INTERVAL'])
    logger = logging.getLogger('ticket-checker')

    # Ghost server (Webkit/Qt)
    ghost = Ghost(qt_debug=True, log_level=logging.DEBUG)

    logger.info('Polling %s for changes' % url)

    while True:

        start = time.clock()
        current_time = strftime("%Y-%m-%d %H:%M:%S")

        logger.debug('Check #%s: %s', check_count, current_time)

        # Get page
        try:
            page = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.info(e)

        # Parse HTML
        try:
            soup = BeautifulSoup(page.text, "lxml")
        except Exception as e:
            logger.info('BS/lxml parse error: %s' % e)

        # Remove dynamic "data-refresh-id" div
        try:
            foo = soup.find("div", class_="entry-content")
            del foo['data-refresh-id']
        except Exception as e:
            print("Error removing dynamic content from html: %s" % e)

        # Get the bit we're interested in.
        # This is just the section with the buttons in.
        # If they add a new section or change the name this will break

        try:
            new_html = soup.find(id='page_outer').extract().prettify()
        except Exception as e:
            logger.info('Error extracting HTML: %s' % e)

        comp = ['-', '+', '?']
        diff = '\n'.join(difflib.ndiff(current_page.splitlines(), new_html.splitlines()))

        # Read the first char of each line in the diff into a list
        # If HTML differs it'll contain diff characters
        a = []
        for line in io.StringIO(diff):
            a.append(line[:1])

        # If old page and new page differ
        if any(x in a for x in comp):
            current_page = new_html

            # Ignore first check
            if check_count > 1:

                logger.info('Check %d, %s: Page differs' % (check_count, current_time))

                # Get a screen grab of the main content div
                logger.debug('Ghost: capturing page image')
                try:
                    page, page_name = ghost.create_page(prevent_download=["css", "js"])
                    page_resources = page.open(url, wait_onload_event=True)
                    region_of_interest=page.region_for_selector('#page_outer')
                    page.capture_to("tickets_page.png", region=region_of_interest)
                    ghost.remove_page(page_name)
                except Exception as e:
                    logger.info('Ghost error: {}'.format(e))

                if smtp_notify:
                    send_email(current_time, url)

                if sms_notify:
                    send_sms(current_time, url)

        work_duration = time.clock() - start
        snooze = polling_interval - work_duration
        if snooze < 0:
            snooze = 11
        logger.debug('Check #%d, snoozing for %f seconds\n', check_count, snooze)
        check_count += 1
        time.sleep(snooze)


def main():

    parser = argparse.ArgumentParser(
        description='Glastonbury ticket snooper'
    )
    parser.add_argument("-debug", action='store_true', help="Log debug messages")
    parser.add_argument("-sms", action='store_true', help="Send notification SMS (must have Twilio account)")
    parser.add_argument("-email", action='store_true', help="Send notification email (must have gmail account")
    parser.add_argument("-logtofile", help="Path to log to")
    args = parser.parse_args()

    admin_env = ['POLLING_INTERVAL', 'TICKET_URL', 'EMAIL_NOTIFICATIONS', 'SMS_NOTIFICATIONS']
    smtp_env = ['SMTP_FROMADDR', 'SMTP_TOADDRS', 'SMTP_GMAIL_USERNAME', 'SMTP_GMAIL_PASSWORD']
    sms_env = ['TWILIO_ACCTSID', 'TWILIO_ACCTTOKEN', 'TWILIO_NUMBER']

    # Environment variable checks

    for env in admin_env:
        if os.getenv(env) is None:
            print("Ticket/Polling config not set")
            raise SystemExit

    if args.email or os.environ['EMAIL_NOTIFICATIONS'].lower() == 'yes':
        for env in smtp_env:
            if os.getenv(env) is None:
                print("SMTP variables not set")
                raise SystemExit

    if args.sms or os.environ['EMAIL_NOTIFICATIONS'].lower() == 'yes':
        for env in sms_env:
            if os.getenv(env) is None:
                print("SMS variables not set")
                raise SystemExit

    # Logging
    reload(logging)
    logger = logging.getLogger('ticket-checker')

    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if args.debug or os.environ['LOG_DEBUG'].lower() == 'yes':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if args.logtofile is not None:
        fh = logging.FileHandler(args.logtofile, mode='w')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    if args.email or os.environ['EMAIL_NOTIFICATIONS'] == 'yes':
        email_notifications = True
        logger.info("Email notifications are ON")
    else:
        email_notifications = False
        logger.info("Email notifications are OFF")

    if args.email or os.environ['SMS_NOTIFICATIONS'] == 'yes':
        sms_notifications = True
        logger.info("SMS notifications are ON")
    else:
        sms_notifications = False
        logger.info("SMS notifications are OFF")

    check_ticket_site(email_notifications, sms_notifications)

if __name__ == '__main__':
    main()
