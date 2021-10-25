# token = ''

# # from slackclient import SlackClient

# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError

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
signature_verifier = SignatureVerifier(
    signing_secret='secret'
    # signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

from slack_sdk.webhook import WebhookClient

from flask import Flask, request, make_response
app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_app():
    # Verify incoming requests from Slack
    # https://api.slack.com/authentication/verifying-requests-from-slack
    if not signature_verifier.is_valid(
        body=request.get_data(),
        timestamp=request.headers.get("X-Slack-Request-Timestamp"),
        signature=request.headers.get("X-Slack-Signature")):
        return make_response("invalid request", 403)

    # Handle a slash command invocation
    if "command" in request.form \
        and request.form["command"] == "/reply-this":
        response_url = request.form["response_url"]
        text = request.form["text"]
        webhook = WebhookClient(response_url)
        # Send a reply in the channel
        response = webhook.send(text=f"You said '{text}'")
        # Acknowledge this request
        return make_response("", 200)

    return make_response("", 404)

if __name__ == '__main__':
    app.run(threaded=True, port=5000)
