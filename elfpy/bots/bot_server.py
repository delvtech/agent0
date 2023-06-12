"""A simple Flask server to run python scripts."""
import json
import subprocess
import sys
import tempfile

from flask import Flask, jsonify, request

app = Flask(__name__)

# Store the running processes and their corresponding IDs
running_processes: dict[int, subprocess.Popen] = {}


@app.route("/run_script", methods=["POST"])
def run_script():
    """Run a python script and return the script id."""
    # TODO: validate the json
    data = request.json

    # Save the JSON payload to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        json_data = json.dumps(data).encode("utf-8")
        temp_file.write(json_data)
        temp_file_path = temp_file.name

    # Execute the python script with the provided JSON as an argument
    script_id = len(running_processes) + 1
    script_path = app.config["SCRIPT_PATH"]
    with subprocess.Popen(["python", script_path, temp_file_path]) as process:
        # Store the process in the dictionary
        running_processes[script_id] = process

    return jsonify({"id": script_id}), 200


@app.route("/kill_script", methods=["POST"])
def kill_script():
    """Kill a running python script."""
    if not request.json:
        return jsonify({"message": "Invalid request. Please provide a valid ID."}), 400
    try:
        script_id = int(request.json["id"])
    except (KeyError, ValueError):
        return jsonify({"message": "Invalid request. Please provide a valid ID."}), 400

    # Check if the script is running
    if script_id in running_processes:
        process = running_processes[script_id]
        process.kill()
        del running_processes[script_id]
        return jsonify({"message": f"Script with ID {script_id} has been killed."}), 200

    return jsonify({"message": f"Script with ID {script_id} is not running."}), 404


@app.route("/list_processes", methods=["GET"])
def list_processes():
    """List all running python scripts."""
    process_list = [{"id": script_id, "status": process.poll()} for script_id, process in running_processes.items()]
    return jsonify({"processes": process_list}), 200


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app.py <script_path>")
        sys.exit(1)

    SCRIPT_PATH = sys.argv[1]
    app.config["SCRIPT_PATH"] = SCRIPT_PATH

    app.run()
