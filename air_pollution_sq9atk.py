#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

import urllib.request, urllib.error, urllib.parse
import logging
import json
import socket

from pprint import pprint

# LISTA STACJI Z NUMERAMI
# http://api.gios.gov.pl/pjp-api/rest/station/findAll

from sr0wx_module import SR0WXModule


class AirPollutionSq9atk(SR0WXModule):
    """Klasa pobierająca info o zanieczyszczeniach powietrza"""

    def __init__(self, language, service_url, city_id=1, station_id=3):
        self.__language = language
        self.__service_url = service_url
        self.__station_id = station_id
        self.__logger = logging.getLogger(__name__)

        self.__stations_url = "station/findAll/"
        self.__station_url = "station/sensors/"
        self.__sensor_url = "data/getData/"
        self.__index_url = "aqindex/getIndex/"

    def getJson(self, url):
        self.__logger.info("::: Odpytuję adres: " + url)

        try:
            data = urllib.request.urlopen(url, None, 45)
            return json.load(data)
        except urllib.error.URLError as e:
            self.__logger.error("Connection error", exc_info=e)
        except socket.timeout:
            self.__logger.error("Connection timed out!")

        return {}

    def getStationName(self):
        url = self.__service_url + self.__stations_url
        stationName = ''
        for station in self.getJson(url):
            if station['id'] == self.__station_id:
                stationName = station['stationName']
        return stationName

    def getSensorValue(self, sensorId):
        url = self.__service_url + self.__sensor_url + str(sensorId)
        data = self.getJson(url)
        if data['values'][0]['value']:  # czasem tu schodzi null
            value = data['values'][0]['value']
        else:
            value = data['values'][1]['value']
        return [
            data['key'],
            value
        ]

    def getLevelIndexData(self):
        url = self.__service_url + self.__index_url + str(self.__station_id)
        return self.getJson(url)

    def getSensorsData(self):
        url = self.__service_url + self.__station_url + str(self.__station_id)
        levelIndexArray = self.getLevelIndexData()
        sensors = []
        for row in self.getJson(url):
            value = self.getSensorValue(row['id'])
            if value[1] > 1:  # czasem tu schodzi none
                qualityIndexName = self.safe_name(value[0]) + "IndexLevel"
                if qualityIndexName in levelIndexArray:
                    index = levelIndexArray[qualityIndexName]['indexLevelName']
                else:
                    index = 'empty'
                sensors.append([
                    row['id'],
                    qualityIndexName,
                    self.safe_name(row['param']['paramName']),
                    value[1],
                    self.safe_name(index)
                ])
        if len(sensors) > 0:
            return sensors
        else:
            raise RuntimeError("brak danych pomiarowych")

    def prepareMessage(self, data):
        levels = {
            'bardzo_dobry': 'poziom_bardzo_dobry _ ',
            'dobry': 'poziom_dobry _ ',
            'dostateczny': 'poziom_dostateczny _ ',
            'umiarkowany': 'poziom_umiarkowany _ ',
            'zly': 'poziom_zl_y _ ',  # ten jest chyba nieuzywany
            'zl_y': 'poziom_zl_y _ ',
            'bardzo_zly': 'poziom_bardzo_zl_y _ ',  # ten też jest chyba nieuzywany
            'bardzo_zl_y': 'poziom_bardzo_zl_y _ ',
            'empty': ''
        }
        message = " "
        for row in data:
            message += " " + row[2]
            message += " " + self.__language.read_micrograms(int(row[3]))
            message += " " + levels[row[4]]
        return message

    def get_data(self):
        self.__logger.info("::: Pobieram informacje o skażeniu powietrza...")
        self.__logger.info("::: Przetwarzam dane...\n")

        sensorsData = self.getSensorsData()
        valuesMessage = self.prepareMessage(sensorsData)

        message = " _ informacja_o_skaz_eniu_powietrza _ "
        message += " stacja_pomiarowa " + self.safe_name(self.getStationName()) + " _ "
        message += valuesMessage

        return {
            "message": message,
            "source": "powietrze_malopolska_pl",
        }
