import json
import os
import mimetypes
import smtplib, ssl

from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage

from pymongo import MongoClient
import requests

caught, score, spot, images = {}, {}, {}, {}

# DB_PATH = "db/"
# DB = {
#     "caughtboard.json": caught,
#     "scoreboard.json": score,
#     "spotboard.json": spot,
#     "images.json": images
# }

# def init_db():
#     try:
#         os.mkdir(DB_PATH[:-1])
#     except:
#         return
#     for disk in DB:
#         with open(DB_PATH + disk, 'w') as f:
#             json.dump({}, f, indent=4)

# def read_db():
#     for disk, memory in DB.items():
#         with open(DB_PATH + disk, 'r') as f:
#             memory.update(json.load(f))
#     return caught, score, spot, images

# def write_db(*args):
#     for data, disk in zip(args, DB):
#         with open(DB_PATH + disk, 'w') as f:
#             json.dump(data, f, indent=4)

# # https://betterprogramming.pub/how-to-send-emails-with-attachments-using-python-dd37c4b6a7fd
# def email_db():
#     # port = 465  # For SSL
#     port = int(os.environ.get("SMTP_PORT")) # For TLS
#     password = os.environ.get("PASSWORD")

#     # Create a secure SSL context
#     context = ssl.create_default_context()

#     with smtplib.SMTP(os.environ.get("SMTP_ADDRESS"), port) as smtp:
#         smtp.ehlo()
#         smtp.starttls(context=context)
#         smtp.ehlo()
#         sender = os.environ.get("SENDER_ADDRESS")
#         smtp.login(sender, password)
        
#         message = EmailMessage()
#         message["Subject"] = "cbspotbot data"
#         message["From"] = sender
#         message["To"] = os.environ.get("RECEIVER_ADDRESS")

#         for filename in DB:
#             path = f'{DB_PATH}{filename}'

#             # Guess the content type based on the file's extension.
#             ctype, encoding = mimetypes.guess_type(path)
#             if ctype is None or encoding is not None:
#                 ctype = 'application/octet-stream'
#             maintype, subtype = ctype.split('/', 1)

#             with open(path, 'rb') as fp:
#                 message.add_attachment(fp.read(), maintype=maintype, subtype=subtype, 
#                                 filename=filename)
#         smtp.send_message(message)

def setup_db():
    client = MongoClient(f'mongodb+srv://{os.environ.get("DB_USER")}:{os.environ.get("PASSWORD")}@cluster0.xzki5.mongodb.net/codespotting?retryWrites=true&w=majority')
    db = client.get_database('spottings')
    db_caught, db_spot, db_images = db.get_collection('caught'), db.get_collection('spot'), db.get_collection('images')
    return db_caught, db_spot, db_images

def insert_db(*args):
    for collection, data in args:
        for entry in data:
            try:
                collection.insert_one({"_id": entry, "data": data[entry]})
            except:
                collection.update_one({"_id": entry}, {'$set': {"data": data[entry]}})
