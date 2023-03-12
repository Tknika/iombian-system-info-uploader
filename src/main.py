#!/usr/bin/env python3

import logging
import signal
import time

from communication_module import CommunicationModule
from firestore_system_info_handler import FirestoreSystemInfoHandler
from sub_client import SubClient

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s - %(name)-16s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def stop():
    logger.info("Stopping IoMBian Services Uploader Service")
    if firestore_system_info_handler:
        firestore_system_info_handler.stop()
    if system_info_client:
        system_info_client.stop()
    if comm_module:
        comm_module.stop()


def signal_handler(sig, frame):
    stop()


def on_db_system_info_updated(system_info):
    global firestore_system_info_cache
    logger.debug(f"Database system info updated: {system_info}")
    firestore_system_info_cache = system_info


def on_system_info_message(message):
    system_info = filter_message(message)
    logger.debug(f"New system info message received: {system_info}")
    if system_info != firestore_system_info_cache:
        logger.info("Database system info is different, synchronize it")
        firestore_system_info_handler.update_system_info(system_info)


def filter_message(message):
    keys_to_delete = ["system_time", "uptime"]
    filtered_message = {k: v for k,
                        v in message.items() if k not in keys_to_delete}
    return filtered_message


if __name__ == "__main__":
    logger.info("Starting IoMBian System Info Uploader Service")

    comm_module, firestore_system_info_handler, system_info_client = None, None, None

    comm_module = CommunicationModule(host="127.0.0.1", port=5555)
    comm_module.start()

    api_key = comm_module.execute_command("get_api_key")
    project_id = comm_module.execute_command("get_project_id")
    refresh_token = comm_module.execute_command(
        "get_refresh_token")
    device_id = comm_module.execute_command("get_device_id")

    firestore_system_info_cache = None
    firestore_system_info_handler = FirestoreSystemInfoHandler(
        api_key, project_id, refresh_token, device_id, on_db_system_info_updated)
    firestore_system_info_handler.start()

    while(firestore_system_info_cache == None):
        time.sleep(0.1)

    system_info_client = SubClient(host="127.0.0.1", port=5557)
    system_info_client.set_message_callback(on_system_info_message)
    system_info_client.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.pause()
