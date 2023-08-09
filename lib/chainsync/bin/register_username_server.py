"""A simple Flask server to run python scripts."""
import logging

from chainsync.db.base import interface
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_expects_json import expects_json

app = Flask(__name__)


json_schema = {
    "type": "object",
    "properties": {"wallet_addrs": {"type": "array", "items": {"type": "string"}}, "username": {"type": "string"}},
    "required": ["wallet_addrs", "username"],
}


@app.route("/register_bots", methods=["POST"])
@expects_json(json_schema)
def register_bots():
    """Registers a list of wallet addresses to a username via post request"""
    # TODO: validate the json
    data = request.json
    if data is not None:
        wallet_addrs: list[str] = data["wallet_addrs"]
        username: str = data["username"]
    else:
        return jsonify({"data": data, "error": "request.json is None"}), 500

    # initialize the postgres session
    session = interface.initialize_session()
    try:
        interface.add_user_map(username, wallet_addrs, session)
        logging.debug("Registered wallet_addrs=%s to username=%s}", wallet_addrs, username)
        out = (jsonify({"data": data, "error": ""}), 200)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Ignoring broad exception, since we're simply printing out error and returning to client
        out = (jsonify({"data": data, "error": str(exc)}), 500)

    interface.close_session(session)
    return out


if __name__ == "__main__":
    # Get postgres env variables if exists
    load_dotenv()
    app.run(host="0.0.0.0", port=5002)
