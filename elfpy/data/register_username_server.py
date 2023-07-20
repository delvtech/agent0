"""A simple Flask server to run python scripts."""
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from elfpy.data import postgres

app = Flask(__name__)


@app.route("/register_bots", methods=["POST"])
def register_bots():
    """Run a python script and return the script id."""
    # TODO: validate the json
    data = request.json

    # initialize the postgres session
    session = postgres.initialize_session()
    try:
        # Typing doesn't work with request objects
        wallet_addrs: list[str] = data["wallet_addrs"]  # type:ignore
        username: str = data["username"]  # type:ignore
        postgres.add_user_map(username, wallet_addrs, session)
        # TODO move this to logging
        print(f"Registered {wallet_addrs=} to {username=}")
        out = (jsonify({"data": data, "error": ""}), 200)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Ignoring broad exception, since we're simply printing out error and returning to client
        out = (jsonify({"data": data, "error": str(exc)}), 500)

    postgres.close_session(session)
    return out


if __name__ == "__main__":
    # Get postgres env variables if exists
    load_dotenv()
    app.run(host="localhost", port=5001)
