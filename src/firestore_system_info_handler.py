#!/usr/bin/env python3

from firestore_client_handler import FirestoreClientHandler
import logging
import threading

logger = logging.getLogger(__name__)


class FirestoreSystemInfoHandler(FirestoreClientHandler):

    KEYWORD = "system_info"
    RESTART_DELAY_TIME_S = 0.5

    def __init__(self, api_key, project_id, refresh_token, device_id, system_info_update_callback=lambda _: None):
        super().__init__(api_key, project_id, refresh_token)
        self.device_id = device_id
        self.users_path = None
        self.devices_path = None
        self.system_info_update_callback = system_info_update_callback
        self.device_subscription = None
        self.system_info_cache = None

    def start(self):
        logger.debug("Starting Firestore System Info Handler")
        self.initialize_client()

    def stop(self):
        logger.debug("Stopping Firestore System Info Handler")
        if self.device_subscription:
            self.device_subscription.unsubscribe()
            self.device_subscription = None
        self.stop_client()

    def restart(self):
        logger.debug("Restarting Firestore System Info Handler")
        self.stop()
        self.start()

    def on_client_initialized(self):
        logger.info("Firestore client initialized")
        self.devices_path = f"users/{self.user_id}/devices"
        if self.device_subscription:
            return
        self.device_subscription = self.client.collection(self.devices_path).document(
            self.device_id).on_snapshot(self._on_device_update)

    def on_server_not_responding(self):
        logger.error("Firestore server not responding")
        threading.Timer(self.RESTART_DELAY_TIME_S, self.restart).start()

    def on_token_expired(self):
        logger.debug("Refreshing Firebase client token id")
        threading.Timer(self.RESTART_DELAY_TIME_S, self.restart).start()

    def update_system_info(self, system_info):
        self.initialize_client(notify=False)
        if not self.client:
            logger.debug(
                "Firebase client not ready, cannot update system info")
            return
        updated_field = {f"{self.KEYWORD}": system_info}
        try:
            self.client.collection(self.devices_path).document(
                self.device_id).update(updated_field, timeout=2)
        except Exception as e:
            logger.error("Firebase client error, restart the handler")
            threading.Timer(self.RESTART_DELAY_TIME_S, self.restart).start()

    def _on_device_update(self, document_snapshot, changes, read_time):
        if len(document_snapshot) != 1:
            return
        device_info = document_snapshot[0].to_dict()

        if not self.KEYWORD in device_info:
            logger.warn(
                f"'{self.KEYWORD}' information not available, creating the new field")
            updated_field = {f"{self.KEYWORD}": {}}
            self.client.collection(self.devices_path).document(
                self.device_id).update(updated_field)
            return

        system_info = device_info.get(self.KEYWORD)

        if system_info != self.system_info_cache:
            self.system_info_cache = system_info
            self.system_info_update_callback(system_info)
