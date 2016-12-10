
**Glasto ticket checker**

'A friend' didn't remember to pay for their Glastonbury ticket. Rumours
abound of tickets appearing randomly on the ticket site, which aren't
advertised but still manage to get snapped up within moments. I wrote
this to give the friend a fighting chance of catching on of these
elusive unicorn tickets.

**Setup**

A Dockerfile is included to bootstrap an image which will run the
code.

To send email you'll need a gmail account and [turn on access for less
secure apps](https://support.google.com/accounts/answer/6010255?hl=en)

To send SMS you'll need a [Twilio account](https://www.twilio.com/)

**Environment variables**

```dockerfile
ENV POLLING_INTERVAL 10         # x seconds (less than 10 will cause issues)
ENV TICKET_URL 'http://glastonbury.seetickets.com/content/extras'
ENV LOG_DEBUG 'no'              # yes/no
ENV EMAIL_NOTIFICATIONS 'no'    # yes/no
ENV SMTP_FROMADDR ''            # '<youremail>@gmail.com'
ENV SMTP_TOADDRS ''             # '1@foo.com, 2@bar.com' etc
ENV SMTP_GMAIL_USERNAME ''      # '<youremail>@gmail.com'
ENV SMTP_GMAIL_PASSWORD ''      # ronseal
ENV SMS_NOTIFICATIONS 'no'      # yes/no
ENV TWILIO_ACCTSID ''           # SID string
ENV TWILIO_ACCTTOKEN ''         # TOKEN string
ENV TWILIO_NUMBER ''            # The number you have added to your twilio acct
ENV SMS_TOADDRS ''              # '+4412345678, +4487654321' etc
```

**How to run**

Once you built the image, run a container and set what notification options you
want to use.

E.g.

```
docker run -e "LOG_DEBUG=yes" \
           -e "EMAIL_NOTIFICATIONS=yes" \
           -e "SMS_NOTIFICATIONS=yes" \
           --restart always \
           --name foo
           <image>
```
