#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import logging
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from sr0wx_module import SR0WXModule


class CalendarSq9atk(SR0WXModule):
    """Klasa pobierająca dane kalendarzowe"""

    def __init__(self, language, service_url, city_id=3094802, **kwargs):
        self.__service_url = service_url
        self.__city_id = city_id
        self.__language = language
        self.__logger = logging.getLogger(__name__)

    def downloadFile(self, url):
        try:
            self.__logger.info("::: Odpytuję adres: " + url)
            webFile = urllib.request.urlopen(url, None, 30)
            return webFile.read()
        except urllib.error.URLError as e:
            self.__logger.error("Connection error", exc_info=e)
        except socket.timeout:
            self.__logger.error("Connection timed out!")

    def getSunsetSunrise(self):
        self.__logger.info("::: Pobieram dane o wschodzie i zachodzie słońca")
        r = re.compile(rb"<h1>(.*)(\d\d:\d\d)(.*)(\d\d:\d\d)</h1>")
        url = self.__service_url + str(self.__city_id)
        html = self.downloadFile(url)
        matches = r.findall(html)
        return {
            "sunrise": matches[0][1],
            "sunset": matches[0][3],
        }

    def hourToNumbers(self, time="00:00"):
        datetime_object = datetime.strptime(time.decode("ascii"), "%H:%M")
        time_words = self.__language.read_datetime(datetime_object, "%H %M")
        return time_words

    def get_data(self):
        times = self.getSunsetSunrise()
        self.__logger.info("::: Przetwarzam dane...\n")

        message = ["_", "kalendarium", "_"]
        message.extend(["wscho_d_sl_on_ca", "godzina"])
        message.extend(self.hourToNumbers(times["sunrise"]).split())
        message.append("_")
        message.extend(["zacho_d_sl_on_ca", "godzina"])
        message.extend(self.hourToNumbers(times["sunset"]).split())
        message.append("_")
        message.append("_")

        return {
            "message": message,
            "source": "calendar_zoznam_sk",
        }


def create(config):
    return CalendarSq9atk(**config)
