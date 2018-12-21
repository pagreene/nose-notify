# nose-notify
This is a simple script that can be used to execute nosetests and send the results to slack or email upon failure. It can be especially useful when running automated tests remotely, such as on Travis.

## Requirements
This is designed and primarily tested in python 3.5, however it is ostensibly python 2.7 compatible for now. You must, of course, have installed `nose` in order to run the nose tests. In addition, to send email, the machine running the tests must have some type of email server set up. The simplest way to start a server using python is:
```bash
python -m smtpd -n -d
```
If you are using slack, you must register a slack bot and provide a web hook as an input argument. The `slackclient` package is *not* needed, however you must have `requests` installed.

## Setup
Simply clone (preferably a fork of) this repo, and add the directory to your python path.

## Usage
All traditional arguments are passed along to nose, so for the most part you can treat this exactly like running `nosetests`. However, there are three new arguments relating to sending the results. To sent an email, the following two arguments must be included:
- `--email` : include an email address to which the failure summary will be sent
- `--name` : the name to use in the email
For example:
```bash
python -m nose_notify -v --email "myaddress@host.com" --name "Foo Barbaz"
```

To sent a slack message, you must include:
- `--slack_hook` : the http address for the webhook you have configured for your slack app.
For example:
```bash
python -m nose_notify -v --slack_hook "https://hooks.slack.com/services/SPECIAL/IDENTIFICATION/STRINGS
```
You can, of course, include all of the above options and send both and email and a slack message.
