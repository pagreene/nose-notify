from __future__ import absolute_import, print_function, unicode_literals
from builtins import dict, str

import re
import socket
import sys
import nose
import smtplib
from time import sleep
from io import BytesIO
from subprocess import Popen, PIPE


class SavedStream(BytesIO):
    """This class is identical to StringIO, but prints write input."""
    def write(self, inp):
        print(inp, end='')
        super(SavedStream, self).write(inp.encode('utf-8'))


def run():
    """Run the nose test(s), capturing the logs as we go."""
    stream = SavedStream()
    nose_config = nose.config.Config(stream=stream)
    nose.run(config=nose_config, argv=sys.argv)
    return stream.getvalue()


def _get_pattern_from_output(proc, pattern, retries=5, wait=1):
    """Get the latest output from the email server."""
    m = None
    err_str = ''
    while m is None and retries:
        sleep(wait)
        try:
            out, err = proc.communicate(timeout=5)
            err_str += err
            m = re.search(pattern, err)
        except Exception:
            print("Communicate timed out...")
            continue
        finally:
            retries -= 1
    return m, err_str


MSG_FMT = """From: Tester <{sender}>
To: {name} <{receiver}>
Subject: Nosetest Results ({version})

{content}
"""
HOST = 'localhost'
PORT = 8025


def start_server():
    print("Starting email server...")
    server_proc = Popen(['python', '-m', 'smtpd', '-n', '-d'], stderr=PIPE,
                        stdout=PIPE)
    m, out_str = _get_pattern_from_output(server_proc,
                                          "Local addr: \(\'(.*?)\',\s+(\d+)\)")
    if m is None:
        server_proc.terminate()
        print("Failed to start email server:")
        print(out_str)
        return None, None
    hostname, port = m.groups()
    print("Servers started on %s at port %s." % (hostname, port))
    return hostname, int(port), server_proc


def extract_summary(message):
    """Get the error summary from the test log."""
    mstr = message.decode('utf-8')
    mlines = mstr.splitlines()
    if not mlines[-1].startswith('FAILED'):
        return None
    for i, line in enumerate(mlines):
        if line == '='*70 or line == '-'*70:
            break
    return '\n'.join(mlines[i:])


def send_email(name, receiver, message):
    """Send an email with the given message."""

    # Send the email.
    sender = 'noreply@' + socket.gethostname()
    summary = extract_summary(message)
    if summary is None:
        # We passed, no need to send an email!
        return True
    smtp_msg = MSG_FMT.format(sender=sender, name=name,
                              content=summary,
                              receiver=receiver,
                              version=sys.version.split(' ')[0])
    smtp = smtplib.SMTP(HOST, port=PORT)
    smtp.sendmail(sender, [receiver], smtp_msg)
    return True


def main():
    result = run()
    sent = send_email('Patrick Greene', 'phystheory4fun@gmail.com', result)
    if not sent:
        sys.exit(1)
    return


if __name__ == '__main__':
    main()
