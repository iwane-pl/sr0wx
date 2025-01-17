#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import logging
import socket
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from sr0wx_module import SR0WXModule


class PropagationSq9atk(SR0WXModule):
    """Klasa pobierająca dane kalendarzowe"""

    def __init__(self, language, service_url, **kwargs):
        self.__service_url = service_url
        self.__language = language
        self.__logger = logging.getLogger(__name__)
        self.__pixels = {
            # niepotrzebne pasma można zaremowac znakiem '#'
            160: {"day": {"x": 50, "y": 60}, "night": {"x": 100, "y": 60}},
            80: {"day": {"x": 50, "y": 95}, "night": {"x": 100, "y": 95}},
            40: {"day": {"x": 50, "y": 140}, "night": {"x": 100, "y": 140}},
            20: {"day": {"x": 50, "y": 185}, "night": {"x": 100, "y": 185}},
            10: {"day": {"x": 50, "y": 230}, "night": {"x": 100, "y": 230}},
            6: {"day": {"x": 50, "y": 270}, "night": {"x": 100, "y": 270}},
        }

        self.__levels = {
            "#17e624": "warunki_podwyzszone",  # zielony
            "#e6bc17": "warunki_normalne",  # żółty
            "#e61717": "warunki_obnizone",  # czerwony
            "#5717e6": "pasmo_zamkniete",  # fioletowy
        }

    def rgb2hex(self, rgb):
        return "#%02x%02x%02x" % rgb

    def downloadImage(self, url):
        try:
            self.__logger.info("::: Odpytuję adres: " + url)
            webFile = urllib.request.URLopener()
            webFile.retrieve(url, "propagacja.png")
            return Image.open("propagacja.png", "r")
        except urllib.error.URLError as e:
            self.__logger.error("Connection error", exc_info=e)
        except socket.timeout:
            self.__logger.error("Connection timed out!")
        except Exception:
            self.__logger.exception("Unexpected error")
            raise

    def collectBandConditionsFromImage(self, image, dayTime):
        try:
            imageData = image.load()
            data = []
            for band in sorted(self.__pixels):
                x = self.__pixels[band][dayTime]["x"]
                y = self.__pixels[band][dayTime]["y"]
                rgba = imageData[x, y]
                color = self.rgb2hex(rgba[:3])

                if color in self.__levels:
                    data.append(f"{band}_metrow")
                    data.append(self.__levels[color])

            return data
        except Exception:
            self.__logger.exception("Error in collecting band conditions")
            return []

    def get_data(self):
        image = self.downloadImage(self.__service_url)

        self.__logger.info("::: Przetwarzam dane...\n")

        message = ["_", "informacje_o_propagacji", "_", "dzien", "_", "_", "pasma", "_"]
        message.extend(self.collectBandConditionsFromImage(image, "day"))
        message.extend(["_", "noc", "_", "_", "pasma", "_"])
        message.extend(self.collectBandConditionsFromImage(image, "night"))
        message.append("_")

        return {
            "message": message,
            "source": "noaa",
        }


def create(config):
    return PropagationSq9atk(**config)
