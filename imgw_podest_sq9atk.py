#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

#   Copyright 2009-2012 Michal Sadowski (sq6jnx at hamradio dot pl)
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import urllib.request, urllib.error, urllib.parse
import re
import json
import logging
import base64
import subprocess

from sr0wx_module import SR0WXModule


class ImgwPodestSq9atk(SR0WXModule):
    """Klasa przetwarza dane informujące o przekroczeniach stanów rzek w regionie."""

    def __init__(self, wodowskazy):
        self.__wodowskazy = wodowskazy
        self.__logger = logging.getLogger(__name__)
        self._dane_wodowskazow = {}

    def zaladujWybraneWodowskazy(self):
        self.__logger.info("::: Pobieram dane o wodowskazach...")
        try:
            jsonData = json.dumps(self.__wodowskazy, separators=(',', ':'))
            b64data = base64.urlsafe_b64encode(jsonData)
            proc = subprocess.Popen("php imgw_podest_sq9atk.php " + b64data, shell=True, stdout=subprocess.PIPE)

            dane = proc.stdout.read()
            self.__logger.info("::: Przetwarzam...")
            self._dane_wodowskazow = json.loads(dane)

        except Exception:
            self.__logger.exception("Nie udało się pobrać danych o wodowskazach!")


    def pobierzDaneWodowskazu(self, wodowskaz):

        if '.' in wodowskaz:
            wodowskaz = wodowskaz.split('.')[1]

        dane = self._dane_wodowskazow[wodowskaz]

        # omijanie zrypanych wodowskazów
        # elif dane['poziom_alarmowy'] == None:
        #   stan = ""
        # elif dane['poziom_ostrzegawczy'] == None:
        #   stan = ""

        if dane['stan_cm'] > dane['poziom_alarmowy']:
            stan = "alarmowy"
        elif dane['stan_cm'] > dane['poziom_ostrzegawczy']:
            stan = "ostrzegawczy"
        else:
            stan = ""

        if dane['tendencja'] == 1:
            tendencja = "tendencja_wzrostowa"
        elif dane['tendencja'] == -1:
            tendencja = "tendencja_spadkowa"
        else:
            tendencja = ""

        return {'numer': wodowskaz,
                'nazwa': dane['nazwa'].strip().encode("utf-8"),
                'nazwa_org': dane['nazwa'].lower().encode("utf-8"),
                'rzeka': dane['rzeka'].strip().encode("utf-8"),
                'stan': dane['stan_cm'],
                'przekroczenieStanu': stan,
                # 'przekroczenieStanuStan': stan,
                'tendencja': tendencja}

    def get_data(self):

        stanyOstrzegawcze = {}
        stanyAlarmowe = {}

        zaladowaneRegiony = []
        self.zaladujWybraneWodowskazy()

        for wodowskaz in self.__wodowskazy:
            region = wodowskaz.split('.')[0]

            if region not in zaladowaneRegiony:
                zaladowaneRegiony.append(region)
                # w = s.pobierzDaneWodowskazu(wodowskaz)
            try:
                w = self.pobierzDaneWodowskazu(wodowskaz)
                rzeka = w['rzeka']
                w['rzeka'] = self.safe_name(w['rzeka'])
                w['nazwa'] = self.safe_name(w['nazwa'])

                id_wodowskazu = wodowskaz + " - " + rzeka + " - " + w['nazwa_org']
                tendencja = w['nazwa'] + ' ' + w['tendencja'] + ' _ '
                if w['przekroczenieStanu'] == 'ostrzegawczy':
                    self.__logger.info("::: Stan ostrzegawczy: %s", id_wodowskazu)
                    if w['rzeka'] not in stanyOstrzegawcze:
                        stanyOstrzegawcze[w['rzeka']] = [tendencja]

                    else:
                        stanyOstrzegawcze[w['rzeka']].append(tendencja)

                elif w['przekroczenieStanu'] == 'alarmowy':
                    self.__logger.info("::: Stan alarmowy: %s", id_wodowskazu)
                    if w['rzeka'] not in stanyAlarmowe:
                        stanyAlarmowe[w['rzeka']] = [tendencja]

                    else:
                        stanyAlarmowe[w['rzeka']].append(tendencja)

                else:
                    self.__logger.debug("Przetwarzam wodowskaz: %s", id_wodowskazu)
            except KeyError:
                self.__logger.exception("::: Brak danych dla wodowskazu %s!!! ", wodowskaz)

        message = "_ _ "
        if stanyOstrzegawcze != {} or stanyAlarmowe != {}:
            message += 'komunikat_hydrologiczny_imgw _ '

            if stanyAlarmowe != {}:
                # Sprawdzenie dla których wodowskazów mamy przekroczone
                # stany alarmowe -- włącz ctcss

                message += ' przekroczenia_stanow_alarmowych '
                for rzeka in sorted(stanyAlarmowe.keys()):
                    message += ' rzeka %s wodowskaz %s ' % (rzeka, " wodowskaz ".join(sorted(stanyAlarmowe[rzeka])),)

            if stanyOstrzegawcze != {}:
                message += '_ przekroczenia_stanow_ostrzegawczych '
                for rzeka in sorted(stanyOstrzegawcze.keys()):
                    message += 'rzeka %s wodowskaz %s ' % (format(rzeka), " wodowskaz ".join(
                        [format(w) for w in sorted(stanyOstrzegawcze[rzeka])]),)

        self.__logger.info("::: Przekazuję przetworzone dane...\n")

        message += ' _ '

        return {
            "message": message,
            "source": "imgw",
        }
