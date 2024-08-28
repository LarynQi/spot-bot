import re
import os

from flask import Flask, request, make_response, jsonify

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk.webhook import WebhookClient

from slack_bolt import App, Say
from slack_bolt.adapter.flask import SlackRequestHandler

from utils import read_db, write_db, read_prev, write_prev, DATABASES, init_db, read_db_name
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)

db_client = MongoClient(f'mongodb+srv://{os.environ.get("DB_USER")}:{os.environ.get("PASSWORD")}@cluster0.xzki5.mongodb.net/codespotting?retryWrites=true&w=majority')

DB_NAME = lambda: read_db_name(db_client)

token = os.environ.get("CLIENT_TOKEN")
client = WebClient(token=token)
SPOT_WORDS = ["spot", "spotted", "spotting", "codespot", "codespotted", "codespotting"]
USER_PATTERN = r"<@[a-zA-Z0-9]+>"

# https://slack.dev/bolt-python/concepts#authenticating-oauth

bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"))

handler = SlackRequestHandler(bolt_app)

@app.route("/slack/events", methods=["POST"])
def handle_events():
    return handler.handle(request)

@bolt_app.event({
    "type": "message",
    "subtype": "file_share"
})
def log_spot(event, say):
    caught, spot, images = read_db(db_client, db_name=DB_NAME())
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
        prev = read_prev(db_client, spotter, db_name=DB_NAME())
        if spotter == prev[0]:
            prev[1] += 1
            if prev[1] >= 3:
                say(f"<@{spotter}> is on fire 🥵")
        else:
            prev[0] = spotter
            prev[1] = 1
        write_prev(db_client, prev, db_name=DB_NAME())
        write_db(db_client, caught, spot, images, db_name=DB_NAME())
        response = client.reactions_add(channel=event['channel'], name="white_check_mark", timestamp=event['ts'])

def scoreboard(event, say, prefix="", db_name=DB_NAME()):
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
    message = prefix + "Spotboard:\n" 
    for i in range(len(scoreboard)):
        curr = scoreboard[i]
        message += f"{i + 1}. {get_display_name(curr[0])} - {curr[1]}\n" 
    say(message)

@bolt_app.message("fa21-scoreboard")
@bolt_app.message("fa21-spotboard")
@bolt_app.message("fa21-Scoreboard")
@bolt_app.message("fa21-Spotboard")
def fa21_scoreboard(event, say):
    scoreboard(event, say, prefix="fa21-", db_name=DATABASES['fa21'])

@bolt_app.message("sp22-scoreboard")
@bolt_app.message("sp22-spotboard")
@bolt_app.message("sp22-Scoreboard")
@bolt_app.message("sp22-Spotboard")
def sp22_scoreboard(event, say):
    scoreboard(event, say, prefix="sp22-", db_name=DATABASES['sp22'])

@bolt_app.message("fa22-scoreboard")
@bolt_app.message("fa22-spotboard")
@bolt_app.message("fa22-Scoreboard")
@bolt_app.message("fa22-Spotboard")
@bolt_app.message("sp23-scoreboard")
@bolt_app.message("sp23-spotboard")
@bolt_app.message("sp23-Scoreboard")
@bolt_app.message("sp23-Spotboard")
def fa22_scoreboard(event, say):
    scoreboard(event, say, prefix="fa22-", db_name=DATABASES['fa22'])

@bolt_app.message("scoreboard")
@bolt_app.message("spotboard")
@bolt_app.message("Scoreboard")
@bolt_app.message("Spotboard")
def curr_scoreboard(event, say):
    scoreboard(event, say, db_name=DB_NAME())

def caughtboard(event, say, prefix="", db_name=DB_NAME()):
    caught, spot, images = read_db(db_client, db_name)
    try:
        words = event['text'].lower().split()
        n = int(words[words.index(prefix + "caughtboard") + 1])
    except:
        n = 5
    caughtboard = sorted(caught.items(), key=lambda p: p[1], reverse=True)[:n]
    message = prefix + "Caughtboard:\n" 
    for i in range(len(caughtboard)):
        curr = caughtboard[i]
        message += f"{i + 1}. {get_display_name(curr[0][2:-1])} - {curr[1]}\n"  
    say(message)

@bolt_app.message("fa21-caughtboard")
@bolt_app.message("fa21-Caughtboard")
def fa21_caughtboard(event, say):
    caughtboard(event, say, prefix="fa21-", db_name=DATABASES['fa21'])

@bolt_app.message("sp22-caughtboard")
@bolt_app.message("sp22-Caughtboard")
def sp22_caughtboard(event, say):
    caughtboard(event, say, prefix="sp22-", db_name=DATABASES['sp22'])

@bolt_app.message("fa22-caughtboard")
@bolt_app.message("fa22-Caughtboard")
@bolt_app.message("sp23-caughtboard")
@bolt_app.message("sp23-Caughtboard")
def fa22_caughtboard(event, say):
    caughtboard(event, say, prefix="fa22-", db_name=DATABASES['fa22'])

@bolt_app.message("caughtboard")
@bolt_app.message("Caughtboard")
def curr_caughtboard(event, say):
    caughtboard(event, say, db_name=DB_NAME())

def pics(event, say, db_name=DB_NAME()):
    caught, spot, images = read_db(db_client, db_name)
    found_spotted = re.search(USER_PATTERN, event['text'])
    if not found_spotted:
        return
    spotted = found_spotted[0]
    message = f"Spots of {get_display_name(spotted[2:-1])}:\n"
    for link in images[spotted]:
        message += f"• {link}\n"
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

@bolt_app.message("sp22-pics")
def sp22_pics(event, say):
    pics(event, say, db_name=DATABASES['sp22'])

@bolt_app.message("fa22-pics")
def fa22_pics(event, say):
    pics(event, say, db_name=DATABASES['fa22'])
    
@bolt_app.message("sp23-pics")
def sp23_pics(event, say):
    pics(event, say, db_name=DATABASES['sp23'])

# https://slack.dev/bolt-python/concepts
@bolt_app.message("pics")
def curr_pics(event, say):
    pics(event, say, db_name=DB_NAME())

def get_display_name(user):
    try:
        profile = bolt_app.client.users_profile_get(user=user)['profile']
        return profile['display_name'] or profile['real_name']
    except:
        print("couldn't find: ", user)

from datetime import datetime

def _reset():
    dt = datetime.now().astimezone().replace(microsecond=0).isoformat()
    new_DB_NAME = init_db(db_client, f'cb|{dt}')
    return new_DB_NAME

@bolt_app.command('/reset')
def reset(ack, respond, command):
    ack()
    # https://api.slack.com/tutorials/uploading-files-with-python
    # respond(f'{str(command)}', response_type='in_channel')
    if 'text' in command and command['text'] == os.environ.get("RESET_PASSWORD"):
        _reset()
        respond('successfully reset db', response_type='in_channel')
    else:
        respond('failed to reset db', response_type='in_channel')

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
