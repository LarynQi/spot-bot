token = ''

# # from slackclient import SlackClient

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import re

# client = WebClient(token)

# try:
#     # response = client.conversations_join(channel='#bot-dev')
#     response = client.chat_postMessage(channel='#bot-dev', text="Hello world!")
#     assert response["message"]["text"] == "Hello world!"
# except SlackApiError as e:
#     assert e.response["ok"] is False
#     assert e.response["error"]
#     print(f"Got an error: {e.response['error']}")

import os
from slack_sdk.signature import SignatureVerifier

from slack_bolt import App, Say
from slack_bolt.adapter.flask import SlackRequestHandler


signature_verifier = SignatureVerifier(
    signing_secret=''
    # signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

from slack_sdk.webhook import WebhookClient

from flask import Flask, request, make_response
from utils import init_db, read_db, write_db, email_db
app = Flask(__name__)

init_db()
caught, score, spot, images = read_db()

# @app.route("/spot", methods=["POST"])
# def spot():
#     # Verify incoming requests from Slack
#     # https://api.slack.com/authentication/verifying-requests-from-slack

#     # print(request.form)
#     request.get_data()
#     if request.form.get('token', '') != 'XMCKbjVB4FN7ajPyDPXSSzMb':
#         print('failed 1.')
#         return make_response("invalid request", 403)
#     # print(request.headers)
#     # request.get_data()
#     if not signature_verifier.is_valid_request(request.data, request.headers):
#         print('failed 2.')
#         return make_response("invalid request", 403)
#     # if not signature_verifier.is_valid(
#     #     body=request.get_data(),
#     #     timestamp=request.headers.get("X-Slack-Request-Timestamp"),
#     #     signature=request.headers.get("X-Slack-Signature")):
#     #     return make_response("invalid request", 403)

#     print("HI", request.form)
#     timestamp = request.headers.get("X-Slack-Request-Timestamp")
#     # Handle a slash command invocation
#     if "command" in request.form \
#         and request.form["command"] == "/spot":
#         response_url = request.form["response_url"]
#         text = request.form["text"]
#         webhook = WebhookClient(response_url)
#         # Send a reply in the channel
#         response = webhook.send(text=f"You said '{text}'")
    
#         client = WebClient(token=token)
#         try:
#             response = client.chat_postMessage(channel='#bot-dev', text="Hello world!")
#             response = client.reactions_add(channel="#bot-dev", name="thumbsup", timestamp=timestamp)
#             assert response["message"]["text"] == "Hello world!"
#         except SlackApiError as e:
#             assert e.response["ok"] is False
#             assert e.response["error"]
#             print(f"Got an error: {e.response['error']}")


#         # Acknowledge this request
#         return make_response("", 200)

#     return make_response("", 404)
# bolt_app = App(token=token)

bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"))
handler = SlackRequestHandler(bolt_app)
@app.route("/slack/events", methods=["POST"])
def handle_events():
    return handler.handle(request)

# @bolt_app.message("spot")
# def respond(event, say):
#     user = event.get("user")
#     print(event)
#     say(f"spotted <@{user}>")
#     client = WebClient(token=token)
#     response = client.reactions_add(channel=event['channel'], name="white_check_mark", timestamp=event['ts'])
#     # response = client.reactions_add(channel="#bot-dev", name="thumbsup", timestamp=payload['ts'])

client = WebClient(token=token)
SPOT_WORDS = ["spot", "spotted", "codespot", "codespotted"]
USER_PATTERN = r"<@[a-zA-Z0-9]{11}>"

prev = [None, None]

@bolt_app.event({
    "type": "message",
    "subtype": "file_share"
})
def log_spot(event, say):
    print(event)

    if any([w in event.get('text', '').lower() for w in SPOT_WORDS]):
        spotter = event['user']
        found_spotted = re.search(USER_PATTERN, event['text'])
        if not found_spotted:
            return
        spotted = found_spotted[0]
        spot[spotter] = spot.get(spotter, 0) + 1
        caught[spotted] = caught.get(spotted, 0) + 1
        for image in event['files']:
            images[spotted] = images.get(spotted, []) + [image['url_private']]
        global prev
        if spotter == prev[0]:
            prev[1] += 1
            if prev[1] >= 3:
                say(f"<@{spotter}> is on fire 🥵")
        else:
            prev[0] = spotter
            prev[1] = 1
        write_db(caught, score, spot, images)
        response = client.reactions_add(channel=event['channel'], name="white_check_mark", timestamp=event['ts'])

@bolt_app.message("scoreboard")
@bolt_app.message("spotboard")
def scoreboard(event, say):
    scoreboard = sorted(spot.items(), key=lambda p: p[1], reverse=True)[:5]
    message = "Spotboard:\n" 
    for i in range(len(scoreboard)):
        curr = scoreboard[i]
        message += f"{i + 1}. <@{curr[0]}> - {curr[1]}\n" 
    say(message)

@bolt_app.message("caughtboard")
def caughtboard(event, say):
    caughtboard = sorted(caught.items(), key=lambda p: p[1], reverse=True)[:5]
    message = "Caughtboard:\n" 
    for i in range(len(caughtboard)):
        curr = caughtboard[i]
        message += f"{i + 1}. {curr[0]} - {curr[1]}\n" 
    say(message)

# TODO
@bolt_app.message("pics")
def pics(event, say):
    found_spotted = re.search(USER_PATTERN, event['text'])
    if not found_spotted:
        return
    spotted = found_spotted[0]
    message = f"Spots of {spotted}:\n"
    for link in images[spotted]:
        message += f"{link}\n"
    print(message)

@bolt_app.event("file_shared")
@bolt_app.event("message")
def ignore():
    pass

import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(func=email_db, trigger="interval", seconds=30)

# https://stackoverflow.com/questions/21214270/how-to-schedule-a-function-to-run-every-hour-on-flask

if __name__ == '__main__':
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    app.run(threaded=True, port=5000)
    # bolt_app.start(5000)
