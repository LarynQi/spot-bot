import re
import os

from flask import Flask, request, make_response

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk.webhook import WebhookClient

from slack_bolt import App, Say
from slack_bolt.adapter.flask import SlackRequestHandler

# from slack_bolt.oauth.oauth_settings import OAuthSettings
# from slack_sdk.oauth.installation_store import FileInstallationStore
# from slack_sdk.oauth.state_store import FileOAuthStateStore

# from utils import init_db, read_db, write_db, email_db, setup_db, insert_db

from utils import read_db, write_db, read_prev, write_prev, DATABASES, DB_NAME 
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)

# init_db()
# caught, score, spot, images = read_db()

db_client = MongoClient(f'mongodb+srv://{os.environ.get("DB_USER")}:{os.environ.get("PASSWORD")}@cluster0.xzki5.mongodb.net/codespotting?retryWrites=true&w=majority')


# caught, spot, images = read_db(db_client)

# print(caught, spot, images)

token = os.environ.get("CLIENT_TOKEN")
client = WebClient(token=token)
SPOT_WORDS = ["spot", "spotted", "spotting", "codespot", "codespotted", "codespotting"]
USER_PATTERN = r"<@[a-zA-Z0-9]+>"

# prev = [None, None]
# prev = read_prev(db_client)

# https://slack.dev/bolt-python/concepts#authenticating-oauth
# oauth_settings = OAuthSettings(
#     client_id=os.environ["SLACK_CLIENT_ID"],
#     client_secret=os.environ["SLACK_CLIENT_SECRET"],
#     scopes=["channels:read", "groups:read", "chat:write"],
#     installation_store=FileInstallationStore(base_dir="./data"),
#     state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data"),
# )

bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"))
# bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"), oauth_settings=oauth_settings)

handler = SlackRequestHandler(bolt_app)

# @app.route("/slack/oauth_redirect", methods=["GET"])
# def handle_oauth():
#     return handler.handle(request)

# @app.route("/slack/install")
# def handle_install():
#     return handler.handle(request)

@app.route("/slack/events", methods=["POST"])
def handle_events():
    return handler.handle(request)

@bolt_app.event({
    "type": "message",
    "subtype": "file_share"
})
def log_spot(event, say):
    caught, spot, images = read_db(db_client)
    if any([w in event.get('text', '').lower() for w in SPOT_WORDS]):
        spotter = event['user']
        found_spotted = re.findall(USER_PATTERN, event['text'])
        if not found_spotted:
            return
        for spotted in found_spotted:
            caught[spotted] = caught.get(spotted, 0) + 1
            for image in event['files']:
                images[spotted] = images.get(spotted, []) + [image['url_private']]
            spot[spotter] = spot.get(spotter, 0) + 1
        prev = read_prev(db_client, spotter)
        if spotter == prev[0]:
            prev[1] += 1
            if prev[1] >= 3:
                say(f"<@{spotter}> is on fire ????")
        else:
            prev[0] = spotter
            prev[1] = 1
        write_prev(db_client, prev)
        # write_db(caught, score, spot, images)
        # print(caught, spot, images)
        write_db(db_client, caught, spot, images)
        response = client.reactions_add(channel=event['channel'], name="white_check_mark", timestamp=event['ts'])

def scoreboard(event, say, prefix="", db_name=DB_NAME):
    caught, spot, images = read_db(db_client, db_name)
    try:
        words = event['text'].lower().split()
        n = int(words[words.index(prefix + "spotboard") + 1])
    except:
        try:
            n = int(words[words.index(prefix + "scoreboard") + 1])
        except:
            n = 5
    scoreboard = sorted(spot.items(), key=lambda p: p[1], reverse=True)[:n]
    message = "Spotboard:\n" 
    for i in range(len(scoreboard)):
        curr = scoreboard[i]
        # message += f"{i + 1}. <@{curr[0]}> - {curr[1]}\n"
        message += f"{i + 1}. {get_display_name(curr[0])} - {curr[1]}\n" 
    say(message)

@bolt_app.message("fa21-scoreboard")
@bolt_app.message("fa21-spotboard")
@bolt_app.message("fa21-Scoreboard")
@bolt_app.message("fa21-Spotboard")
def fa21_scoreboard(event, say):
    scoreboard(event, say, prefix="fa21-", db_name=DATABASES['fa21'])

@bolt_app.message("scoreboard")
@bolt_app.message("spotboard")
@bolt_app.message("Scoreboard")
@bolt_app.message("Spotboard")
def curr_scoreboard(event, say):
    scoreboard(event, say)

def caughtboard(event, say, prefix="", db_name=DB_NAME):
    caught, spot, images = read_db(db_client, db_name)
    try:
        words = event['text'].lower().split()
        n = int(words[words.index(prefix + "caughtboard") + 1])
    except:
        n = 5
    caughtboard = sorted(caught.items(), key=lambda p: p[1], reverse=True)[:n]
    message = "Caughtboard:\n" 
    for i in range(len(caughtboard)):
        curr = caughtboard[i]
        message += f"{i + 1}. {get_display_name(curr[0][2:-1])} - {curr[1]}\n"  
    say(message)

@bolt_app.message("fa21-caughtboard")
@bolt_app.message("fa21-Caughtboard")
def fa21_caughtboard(event, say):
    caughtboard(event, say, prefix="fa21-", db_name=DATABASES['fa21'])

@bolt_app.message("caughtboard")
@bolt_app.message("Caughtboard")
def curr_caughtboard(event, say):
    caughtboard(event, say)

def pics(event, say, db_name=DB_NAME):
    caught, spot, images = read_db(db_client, db_name)
    found_spotted = re.search(USER_PATTERN, event['text'])
    if not found_spotted:
        return
    spotted = found_spotted[0]
    message = f"Spots of {get_display_name(spotted[2:-1])}:\n"
    for link in images[spotted]:
        message += f"??? {link}\n"
    blocks = [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": message
        }
    }]
    say(blocks=blocks, text=message)

@bolt_app.message("fa21-pics")
def fa21_pics(event, say):
    pics(event, say, db_name=DATABASES['fa21'])

# https://slack.dev/bolt-python/concepts
@bolt_app.message("pics")
def curr_pics(event, say):
    pics(event, say)


def get_display_name(user):
    try:
        profile = bolt_app.client.users_profile_get(user=user)['profile']
        return profile['display_name'] or profile['real_name']
    except:
        print("couldn't find: ", user)

@bolt_app.event("file_shared")
@bolt_app.event("message")
def ignore():
    pass

# https://stackoverflow.com/questions/21214270/how-to-schedule-a-function-to-run-every-hour-on-flask

# import time
# import atexit
# from apscheduler.schedulers.background import BackgroundScheduler

# scheduler = BackgroundScheduler()
# scheduler.add_job(func=email_db, trigger="interval", seconds=30)

# from flask_apscheduler import APScheduler

# scheduler = APScheduler()
# scheduler.init_app(app)
# scheduler.start()
# scheduler.add_job(func=email_db, trigger="interval", minutes=30, id='0')


if __name__ == '__main__':
    # scheduler.start()
    # atexit.register(lambda: scheduler.shutdown())
    app.run(threaded=True, port=5000)
    # bolt_app.start(5000)
