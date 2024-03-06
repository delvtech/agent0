"""A simple Flask server to run python scripts."""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify, request
from flask_expects_json import expects_json

from agent0.chainsync.db.base import add_addr_to_username, close_session, initialize_session
from agent0.chainsync.db.hyperdrive import get_current_wallet

app = Flask(__name__)


register_agents_json_schema = {
    "type": "object",
    "properties": {"wallet_addrs": {"type": "array", "items": {"type": "string"}}, "username": {"type": "string"}},
    "required": ["wallet_addrs", "username"],
}


@app.route("/register_agents", methods=["POST"])
@expects_json(register_agents_json_schema)
def register_agents() -> tuple[Response, int]:
    """Registers a list of wallet addresses to a username via post request.

    Returns
    -------
    tuple[Response, int]
        A tuple containing the response and status code of the request.
    """
    # TODO: validate the json
    data = request.json
    if data is not None:
        wallet_addrs: list[str] = data["wallet_addrs"]
        username: str = data["username"]
    else:
        return jsonify({"data": data, "error": "request.json is None"}), 500

    # initialize the postgres session
    # This function gets env variables for db credentials
    session = initialize_session()
    try:
        # Adding suffix since this api is used by bot runners
        add_addr_to_username(username, wallet_addrs, session, user_suffix=" (bots)")
        logging.debug("Registered wallet_addrs=%s to username=%s}", wallet_addrs, username)
        out = (jsonify({"data": data, "error": ""}), 200)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Ignoring broad exception, since we're simply printing out error and returning to client
        out = (jsonify({"data": data, "error": str(exc)}), 500)

    close_session(session)
    return out


balance_of_json_schema = {
    "type": "object",
    "properties": {"wallet_addrs": {"type": "array", "items": {"type": "string"}}},
    "required": ["wallet_addrs"],
}


@app.route("/balance_of", methods=["POST"])
@expects_json(balance_of_json_schema)
def balance_of() -> tuple[Response, int]:
    """Retrieves the balance of a given wallet address from the db.
    Note that this only takes into account token differences from opening and closing
    longs and shorts, not any transfer events between wallets.

    Returns
    -------
    tuple[Response, int]
        A tuple containing the response and status code of the request.
    """
    # TODO: validate the json
    data = request.json
    if data is not None:
        wallet_addrs: list[str] = data["wallet_addrs"]
    else:
        return jsonify({"data": data, "error": "request.json is None"}), 500

    # initialize the postgres session
    # This function gets env variables for db credentials
    session = initialize_session()
    try:
        logging.debug("Querying wallet_addrs=%s for balances}", wallet_addrs)
        current_wallet = get_current_wallet(session, wallet_address=wallet_addrs, coerce_float=False).copy()
        # Avoid exp notation for value field
        # Need a function here to pass to apply, so we use format instead of f-string
        current_wallet["value"] = current_wallet["value"].apply(
            "{:f}".format  # pylint: disable=consider-using-f-string
        )
        # Convert everything else to strings, then convert to json
        data = current_wallet.astype(str).to_json()

        # Convert dataframe to json
        out = (jsonify({"data": data, "error": ""}), 200)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Ignoring broad exception, since we're simply printing out error and returning to client
        out = (jsonify({"data": data, "error": str(exc)}), 500)

    close_session(session)
    return out


def launch_flask(host: str | None = None, port: int | None = None):
    """Launches the flask server

    Arguments
    ---------
    host: str | None, optional
        The host to launch the api server on. Defaults to 0.0.0.0.
    port: int | None, optional
        The port to launch the api server on. Defaults to 5002
    """
    if host is None:
        host = "0.0.0.0"
    if port is None:
        port = 5002

    app.run(host=host, port=port)
