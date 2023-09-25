"""A simple Flask server to run python scripts."""
import argparse

from chainsync.db.api import launch_flask

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Launches the database api server",
    )
    parser.add_argument(
        "--host",
        nargs=1,
        help="The hostname",
        action="store",
        default=[None],
    )
    parser.add_argument(
        "--port",
        nargs=1,
        help="The port",
        action="store",
        default=[None],
    )
    args = parser.parse_args()
    launch_flask(host=args.host[0], port=args.port[0])
