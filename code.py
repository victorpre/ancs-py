# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import board
import busio
import json
import adafruit_drv2605
import adafruit_ble
import usb_cdc

from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble.services.standard import CurrentTimeService
from adafruit_ble_apple_notification_center import AppleNotificationCenterService
from digitalio import DigitalInOut, Direction

#  onboard blue LED
blue_led = DigitalInOut(board.BLUE_LED)
blue_led.direction = Direction.OUTPUT

#  setup for BLE
ble = adafruit_ble.BLERadio()

advertisement = SolicitServicesAdvertisement()
advertisement.complete_name = "CIRCUITPY"

current_status = {
    "type": "setup",
    "content": {
        "status": "starting"
    }
}


#  adds ANCS and current time services for BLE to advertise
advertisement.solicited_services.append(AppleNotificationCenterService)
advertisement.solicited_services.append(CurrentTimeService)

def find_connection():
    for connection in ble.connections:
        if AppleNotificationCenterService not in connection:
            continue
        if not connection.paired:
            connection.pair()
            current_status["content"].update({"status": "connected"})
            display_status()
        return connection, connection[AppleNotificationCenterService]
    return None, None

def display_status():
    data = bytes(json.dumps(current_status), 'utf-8')
    usb_cdc.data.write(data)


def display_notification(notification):
    category = str(notification).split(" ", 1)[0]
    notification_dict = {
        "type": "notification",
        "content": {
            "id": notification.id,
            "category" : category,
            "app_id": notification.app_id,
            "message": notification.message,
            "title": notification.title,
            "subtitle": notification.subtitle,
            "removed": notification.removed
        }
    }
    data = bytes(json.dumps(notification_dict), 'utf-8')
    usb_cdc.data.write(data)
    
active_connection, notification_service = find_connection()

display_status()

while True:
    blue_led.value = False
    if not active_connection:
        ble.start_advertising(advertisement)

    while not active_connection:
        blue_led.value = False
        current_status.update({"type": "setup"})
        current_status["content"].update({"status": "waiting"})
        display_status()
        active_connection, notification_service = find_connection()
        time.sleep(1)
    while active_connection.connected:
        current_status.update({"type": "status"})
        current_status["content"].update({"status": "connected"})
        display_status()
        blue_led.value = True #  blue LED is on when connected
        for current_notification in notification_service.wait_for_new_notifications():
            display_notification(current_notification)
        time.sleep(10)

    current_status["content"].update({"status": "disconnected"})
    display_status()
    active_connection = None
    notification_service = None



