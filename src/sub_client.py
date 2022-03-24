#!/usr/bin/env python3

import logging
import threading
import time
import zmq

logger = logging.getLogger(__name__)


class SubClient(object):

    def __init__(self, topic_filter=None, on_message_callback=None, host="127.0.0.1", port=5556):
        self.topic_filter = topic_filter
        self.on_message_callback = on_message_callback
        self.host = host
        self.port = port
        self.addr = f"tcp://{self.host}:{self.port}"
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.listen_thread = None
        self.listen = False

    def start(self):
        logger.debug(
            f"Starting subscription client ('{self.host}:{self.port}')")
        self.socket.connect(self.addr)
        if self.topic_filter:
            self.socket.subscribe(self.topic_filter)
        else:
            self.socket.subscribe("")

        self.listen = True
        self.listen_thread = threading.Thread(target=self.__listen)
        self.listen_thread.start()

    def stop(self):
        logger.debug("Stopping subcription client")
        self.listen = False
        if self.listen_thread:
            self.listen_thread.join()
            self.listen_thread = None
        self.socket.disconnect(self.addr)
        self.socket.close()
        self.context.term()

    def set_message_callback(self, callback):
        self.on_message_callback = callback

    def __listen(self):
        logger.debug("Starting listen thread")
        while self.listen:
            try:
                message = self.socket.recv_json(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.3)
                continue

            logger.debug(f"Message '{message}' received")
            if self.on_message_callback:
                threading.Thread(target=self.on_message_callback,
                                 args=[message]).start()
        logger.debug("Stopping listen thread")
