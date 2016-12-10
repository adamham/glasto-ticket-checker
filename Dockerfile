FROM phusion/baseimage:0.9.19
MAINTAINER adamh(adamham@gmail.com)

COPY . /usr/local/src
WORKDIR /usr/local/src

RUN apt-get update && apt-get install -y --fix-missing \
    python \
    python-pip \
    qt4-default \
    xvfb \
    python-qt4 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*; \
    pip install --upgrade pip ; \
    pip install -r /usr/local/src/requirements.txt ; \
    pip install -e 'git+git://github.com/carrerasrodrigo/Ghost.py.git#egg=Ghost.py' ; \
    chmod +x /usr/local/src/src/*.py

ENV POLLING_INTERVAL 10         # x seconds
ENV TICKET_URL ''
ENV LOG_DEBUG 'no'              # yes/no
ENV EMAIL_NOTIFICATIONS 'no'    # yes/no
ENV SMTP_FROMADDR ''
ENV SMTP_TOADDRS ''
ENV SMTP_GMAIL_USERNAME ''
ENV SMTP_GMAIL_PASSWORD ''
ENV SMS_NOTIFICATIONS 'no'      # yes/no
ENV TWILIO_ACCTSID ''
ENV TWILIO_ACCTTOKEN ''
ENV TWILIO_NUMBER ''
ENV SMS_TOADDRS ''

CMD ["/usr/local/src/ticket-checker/ticket-checker.py"]

