"""Utilities associated to manipulating Docker."""
import logging
import os
import subprocess
import time
from pathlib import Path

import docker
from docker.errors import DockerException


def check_docker(infra_folder: Path, restart: bool = False) -> None:
    """Check whether docker is running to your liking.

    Arguments
    ---------
    infra_folder : Path
        Path to infra repo folder.
    restart : bool
        Restart docker even if it is running.
    """
    try:
        try:
            _ = docker.from_env()
        except Exception:  # pylint: disable=broad-exception-caught
            home_dir = os.path.expanduser("~")
            socket_path = Path(f"{home_dir}") / ".docker" / "desktop" / "docker.sock"
            if socket_path.exists():
                logging.debug("Docker not found at default socket, using %s..", socket_path)
                _ = docker.DockerClient(base_url=f"unix://{socket_path}")
            else:
                logging.debug("Docker not found.")
                _ = docker.from_env()
        dockerps = _get_docker_ps_and_log()
        number_of_running_services = dockerps.count("\n") - 1
        if number_of_running_services > 0:
            preamble_str = f"Found {number_of_running_services} running services"
            if restart:
                _start_docker(f"{preamble_str}, restarting docker...", infra_folder)
            else:
                logging.info("%s, using them.", preamble_str)
        else:
            _start_docker("Starting docker.", infra_folder)
        logging.info(dockerps)
    except DockerException as exc:
        raise DockerException("Docker not found.") from exc


def _start_docker(startup_str: str, infra_folder: Path) -> None:
    """Bring down docker compose, including volume, pull images, then bring up docker compose.

    Arguments
    ---------
    startup_str : str
        String to log at start.
    infra_folder : Path
        Path to infra repo folder.
    """
    logging.info(startup_str)
    _run_cmd(infra_folder, " && docker-compose down -v", "Shut down docker in ")
    cmd = "docker images | awk 'NR>1 && $2 !~ /none/ && $1 ~ /^ghcr\\.io\\// {print $1 \":\" $2}'"
    output = subprocess.getoutput(cmd)
    if output is not None:
        docker_pull_cmd = f"echo '{output}' | xargs -L1 docker pull"
        _run_cmd(infra_folder, f" && {docker_pull_cmd}", "Updated docker in ")
    else:
        logging.info("No matching images found.")
    _run_cmd(infra_folder, " && docker-compose up -d", "Started docker in ")


def _run_cmd(infra_folder: Path, cmd: str, timing_str: str) -> None:
    """Run a command inside infra_folder, printing out the timing.

    Arguments
    ---------
    infra_folder : Path
        Path to folder in which to run the command.
    cmd : str
        Command to run.
    timing_str : str
        String to print out alonside timing.

    Returns
    -------
    None
    """
    start_time = time.time()
    os.system(f"cd {infra_folder}{cmd}")
    formatted_str = f"{timing_str}{time.time() - start_time:.2f}s"
    logging.info(formatted_str)


def _get_docker_ps_and_log() -> str:
    """Get docker ps using custom table format and log it.

    Returns
    -------
    str
        The command line output of docker ps.
    """
    dockerps = os.popen("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'").read()
    logging.info(dockerps)
    return dockerps
