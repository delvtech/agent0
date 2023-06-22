"""A simple Flask server to run python scripts."""
import json
import os
import subprocess
from dataclasses import asdict, dataclass

from flask import Flask, jsonify

app = Flask(__name__)


# TODO: add container ids or some namespace so we can kill container groups
@dataclass
class AppInfo:
    """App Info"""

    # TODO: don't use hard-coded values, pull these from constants
    eth_port: int = 8545
    artifact_port: int = 80
    ui_port: int = 5173
    botserver_port: int = 5001


# Store the running processes and their corresponding IDs
running_processes: dict[int, AppInfo] = {}


# TODO: Instead of exposing ports, add subroutes that let's us run commands.
# @app.route("/run/{app_id}/{container_id}", methods=["POST"])
# def run_command():
#     """Run a command"""


@app.route("/create_app", methods=["POST"])
def create_app():
    """Run a python script and return the script id."""
    # TODO: allow user to upload config json with flags to pass to setup_env.sh
    # TODO: expose more config options like 'devnet', 'goerli' etc.
    # data = request.json

    # TODO: Set environment variables.  This is where we will update ports set for the different apps.
    # ETH_PORT=8545-8555
    # ARTIFACT_PORT=80-90
    # UI_PORT=5173
    # BOTSERVER_PORT=5001-5011
    os.environ["VAR1"] = "value1"
    os.environ["VAR2"] = "value2"

    # Run the shell script
    script_path = "/home/ubuntu/infra/setup_env.sh"
    subprocess.call(["bash", script_path])
    subprocess.call("docker compose up -d", shell=True)

    script_id = len(running_processes) + 1
    # TODO: don't use hard-coded values here, let's use the smallest value available.
    app_info = AppInfo(eth_port=8545, artifact_port=80, ui_port=5173, botserver_port=5001)
    running_processes[script_id] = app_info
    data = asdict(app_info)

    # Convert the dictionary to JSON
    json_data = json.dumps(data)
    return json_data


@app.route("/list_apps", methods=["GET"])
def list_apps():
    """List all running python scripts."""
    process_list = [{"id": script_id, "info": app_info} for script_id, app_info in running_processes.items()]
    return jsonify({"processes": process_list}), 200


@app.route("/kill", methods=["POST"])
def kill_app():
    """kill an app."""
    # TODO:
    process_list = [{"id": script_id, "info": app_info} for script_id, app_info in running_processes.items()]
    return jsonify({"processes": process_list}), 200


if __name__ == "__main__":
    # TODO: don't hard-code port, pull from environment
    app.run(host="0.0.0.0", port=8080)
