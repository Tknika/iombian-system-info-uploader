#!/usr/bin/env python3

from firestore_handler import FirestoreHandler
import logging

logger = logging.getLogger(__name__)


class FirestoreSystemInfoHandler(FirestoreHandler):

    KEYWORD = "system_info"

    def __init__(self, api_key, project_id, refresh_token, device_id):
        super().__init__(api_key, project_id, refresh_token, self.__on_expired_token)
        self.device_id = device_id
        self.users_path = None
        self.devices_path = None
        self.system_info_update_callback = None
        self.device_subscription = None
        self.system_info_cache = None

    def start(self):
        logger.debug("Starting Firestore System Info Handler")
        self.initialize_db()

    def stop(self):
        logger.debug("Stopping Firestore System Info Handler")
        if self.device_subscription:
            self.device_subscription.unsubscribe()
            self.device_subscription = None
        if self.db:
            self.stop_db()

    def initialize_db(self):
        super().initialize_db()
        if not self.db:
            logger.error("DB connection not ready")
            return
        self.devices_path = f"users/{self.user_id}/devices"
        if not self.device_subscription:
            self.device_subscription = self.db.collection(self.devices_path).document(
                self.device_id).on_snapshot(self.__on_device_update)

    def update_system_info(self, system_info):
        if not self.db:
            self.initialize_db()
        updated_field = {f"{self.KEYWORD}": system_info}
        self.db.collection(self.devices_path).document(
            self.device_id).update(updated_field)

    def add_system_info_update_callback(self, callback):
        self.system_info_update_callback = callback

    def __on_device_update(self, document_snapshot, changes, read_time):
        if len(document_snapshot) != 1:
            return
        device_info = document_snapshot[0].to_dict()

        if not self.KEYWORD in device_info:
            logger.warn(
                f"'{self.KEYWORD}' information not available, creating the new field")
            updated_field = {f"{self.KEYWORD}": {}}
            self.db.collection(self.devices_path).document(
                self.device_id).update(updated_field)
            return

        system_info = device_info.get(self.KEYWORD)

        if system_info != self.system_info_cache:
            self.system_info_cache = system_info
            self.system_info_update_callback(system_info)

    def __on_expired_token(self):
        logger.debug("Refreshing Token Id")
        if self.device_subscription:
            self.device_subscription.unsubscribe()
            self.device_subscription = None
        self.db = None
        self.initialize_db()
