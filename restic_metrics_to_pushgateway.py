#!/usr/bin/env python3

import argparse
import json
import logging
import ssl
import sys
import subprocess

from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request


# Define and parse arguments
parser = argparse.ArgumentParser(
    description="Send metrics of latest restic snapshot to Prometheus Pushgateway."
)
parser.add_argument(
    "--loglevel",
    dest="loglevel",
    action="store",
    default="INFO",
    help="log level (default: INFO)",
    choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
)
parser.add_argument(
    "--pushgateway_url",
    dest="url",
    action="store",
    help='Prometheus Pushgateway URL (e.g. "http://pushgateway.example.org:9091/metrics/job/some_job/instance/some_instance")',
    required=True,
)
parser.add_argument(
    "--tls_skip_verify",
    dest="tls_skip_verify",
    action="store_true",
    help="Skip TLS certificate verification.",
)
args = parser.parse_args()


# Initialize logging
logging.basicConfig(level=args.loglevel, format="%(asctime)s %(levelname)s %(message)s")


# Get snapshot data from restic and parse JSON response
try:
    proc = subprocess.Popen(
        ["restic", "snapshots", "--latest", "1", "--compact", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, error = proc.communicate()
    if proc.returncode:
        raise Exception(error)
    json_object = json.loads(output)
except ValueError as error:
    logging.error("Decoding JSON response failed")
    sys.exit(1)
except Exception as error:
    logging.error(error)
    sys.exit(1)


# Create metrics POST body
data = "# TYPE restic_last_snapshot counter\n"
for snapshot in json_object:
    paths = ",".join(sorted(snapshot["paths"]))
    time = datetime.fromisoformat(snapshot["time"].split('.')[0]).timestamp()
    if snapshot["tags"]:
        tags = ",".join(sorted(snapshot["tags"]))
        data += f'restic_last_snapshot{{hostname="{snapshot["hostname"]}",username="{snapshot["username"]}",paths="{paths}",tags="{tags}"}} {time}\n'
    else:
        data += f'restic_last_snapshot{{hostname="{snapshot["hostname"]}",username="{snapshot["username"]}",paths="{paths}"}} {time}\n'

logging.debug(data.strip().replace("\n", "\n\t"))


# Send data to Pushgateway
request = Request(args.url, headers={}, data=data.encode())

ctx = ssl.create_default_context()
if args.tls_skip_verify:
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

try:
    with urlopen(request, timeout=10, context=ctx) as response:
        logging.info("%s - %d %s", args.url, response.status, response.msg)
except HTTPError as error:
    logging.error("%s - %d %s", args.url, error.status, error.reason)
except URLError as error:
    logging.error("%s - %s", args.url, error.reason)
except TimeoutError:
    logging.error("%s - %s", args.url, "Request timed out")
