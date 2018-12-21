from __future__ import absolute_import, print_function, unicode_literals
from builtins import dict, str

import re
import os
import sys
import json
import nose
import socket
import smtplib
import requests
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
    cfg_files = nose.config.all_config_files()
    manager = nose.plugins.manager.DefaultPluginManager()
    nose_config = nose.config.Config(env=os.environ, files=cfg_files,
                                     plugins=manager, stream=stream)
    nose.run(config=nose_config)
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
Subject: Nosetest Results ({version}) {cmd}

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


def send_email(name, receiver, message, cmd):
    """Send an email with the given message."""

    # Send the email.
    sender = 'noreply@' + socket.gethostname()
    summary = extract_summary(message)
    if summary is None:
        # We passed, no need to send an email!
        return True
    smtp_msg = MSG_FMT.format(sender=sender, name=name, cmd=cmd,
                              content=summary, receiver=receiver,
                              version=sys.version.split(' ')[0])
    smtp = smtplib.SMTP(HOST, port=PORT)
    smtp.sendmail(sender, [receiver], smtp_msg)
    return True


def send_slack_message(hook, message, cmd):
    """Send a slack message with the results."""
    summary = extract_summary(message)
    message = "Nosetests failed when running: %s" % cmd
    data_json = {'text': message,
                 'attachments': [{'color': 'danger',
                                  'text': '```%s```' % summary}]}
    resp = requests.post(hook, data=json.dumps(data_json),
                         headers={'Content-type': 'application/json'})
    if resp.status_code is not 200:
        print("Message failed to send.")
        print(resp.reason)
    return


def pop_argv(args, key):
    val = None
    if key in args:
        idx = args.index(key)
        args.pop(idx)
        val = args.pop(idx)
    return val


def main():
    args = sys.argv
    print(args)
    email = pop_argv(args, '--email')
    name = pop_argv(args, '--name')
    hook = pop_argv(args, '--slack_hook')

    cmd = ' '.join(['nosetests'] + sys.argv[1:])
    print(cmd)
    result = run()
    if hook:
        send_slack_message(hook, result, cmd)
    if name and email:
        sent = send_email(name, email, result, cmd)
        if not sent:
            sys.exit(1)
    return


if __name__ == '__main__':
    main()
