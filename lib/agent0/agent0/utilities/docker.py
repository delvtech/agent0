"""Utilities associated to manipulating Docker."""
import subprocess
import logging
import os
import time
from pathlib import Path


def check_docker(restart: bool = False) -> None:
    """Check whether docker is running to your liking.

    Parameters
    ----------
    restart: bool
        Restart docker even if it is running.
    """
    home_infra = Path(os.path.expanduser("~")) / "code" / "infra"
    if os.path.exists(home_infra):
        infra_folder = home_infra
    else:
        infra_folder = Path("/code/infra")
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
    dockerps = os.popen("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'").read()
    logging.info(dockerps)


def _start_docker(startup_str: str, infra_folder: Path):
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


def _run_cmd(infra_folder: Path, cmd: str, timing_str: str):
    result = time.time()
    os.system(f"cd {infra_folder}{cmd}")
    formatted_str = f"{timing_str}{time.time() - result:.2f}s"
    logging.info(formatted_str)
    return result


def _get_docker_ps_and_log() -> str:
    dockerps = os.popen("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'").read()
    logging.info(dockerps)
    return dockerps
