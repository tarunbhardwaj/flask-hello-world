import json
import sqlite3
from os import getenv
from flask import Flask, request, g

from featureflag import FeatureFlags

app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("database.db")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def add_message(message, type="prod", payload={}):
    db = get_db()
    payload.update(
        {
            "message": message,
        }
    )
    if type == "test":
        payload["test"] = True

    db.cursor().execute(f"Insert into message values('{json.dumps(payload)}')")
    db.commit()


@app.route("/")
def index():
    return "Hello world"


@app.route("/api/messages")
def list_messages():
    db = get_db()
    messages = db.cursor().execute("select * from message")
    message_count = db.cursor().execute("select count(*) from message").fetchone()
    return {"Response": "ok", "messages": messages, "total_messages": message_count}


@app.route("/api/messages", methods=["POST"])
def create_messages():
    # TODO: Validate existing payload
    # {
    #   "message": "" // required
    #   "type": "" // required
    #   "payload": {} // optional
    # }
    data = request.json

    if "payload" in data and not FeatureFlags.get("PAYLOAD_ENABLED"):
        raise Exception("You havn't paid for Payload feature.")

    add_message(data["message"], data["type"], data.get("payload"))


if __name__ == "__main__":
    # Enable featureflags
    FeatureFlags["PAYLOAD_ENABLED"] = getenv("PAYLOAD_ENABLED")

    # DB INIT
    with app.app_context():
        db = get_db()
        db.cursor().execute("""
            create table message (
                payload char
            );
        """)
        db.commit()

    # Create test messages
    with app.app_context():
        add_message("message 1", "test")
        add_message("message 2", "Production")
        add_message("message 3", payload={"numbers": [1, 2, 3]})
        add_message("message 4", "Production")

    app.run(host="0.0.0.0", port=5000)
