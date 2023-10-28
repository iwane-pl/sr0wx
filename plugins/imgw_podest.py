#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
import base64
import json
import logging
import os.path
import subprocess

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

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from sr0wx_module import SR0WXModule


class ImgwPodestSq9atk(SR0WXModule):
    """Klasa przetwarza dane informujące o przekroczeniach stanów rzek w regionie."""

    def __init__(self, **kwargs):
        with open(os.path.join("assets", "wodowskazy.toml"), "rb") as f:
            self.__wodowskazy = tomllib.load(f)
        self.__logger = logging.getLogger(__name__)
        self._dane_wodowskazow = {}

    def zaladujWybraneWodowskazy(self):
        self.__logger.info("::: Pobieram dane o wodowskazach...")
        try:
            jsonData = json.dumps(self.__wodowskazy, separators=(",", ":"))
            b64data = base64.urlsafe_b64encode(jsonData.encode("utf-8"))
            proc = subprocess.Popen(
                "php imgw_podest_sq9atk.php " + b64data.decode("ascii"),
                shell=True,
                stdout=subprocess.PIPE,
            )

            dane = proc.stdout.read()
            self.__logger.info("::: Przetwarzam...")
            self._dane_wodowskazow = json.loads(dane)

        except Exception:
            self.__logger.exception("Nie udało się pobrać danych o wodowskazach!")
            self._dane_wodowskazow = {}

    def pobierzDaneWodowskazu(self, wodowskaz):
        if "." in wodowskaz:
            wodowskaz = wodowskaz.split(".")[1]

        dane = self._dane_wodowskazow[wodowskaz]

        # omijanie zrypanych wodowskazów
        # elif dane['poziom_alarmowy'] == None:
        #   stan = ""
        # elif dane['poziom_ostrzegawczy'] == None:
        #   stan = ""

        if dane["stan_cm"] > dane["poziom_alarmowy"]:
            stan = "alarmowy"
        elif dane["stan_cm"] > dane["poziom_ostrzegawczy"]:
            stan = "ostrzegawczy"
        else:
            stan = ""

        if dane["tendencja"] == 1:
            tendencja = "tendencja_wzrostowa"
        elif dane["tendencja"] == -1:
            tendencja = "tendencja_spadkowa"
        else:
            tendencja = ""

        return {
            "numer": wodowskaz,
            "nazwa": dane["nazwa"].strip().encode("utf-8"),
            "nazwa_org": dane["nazwa"].lower().encode("utf-8"),
            "rzeka": dane["rzeka"].strip().encode("utf-8"),
            "stan": dane["stan_cm"],
            "przekroczenieStanu": stan,
            # 'przekroczenieStanuStan': stan,
            "tendencja": tendencja,
        }

    @property
    def get_data(self):
        message = " "

        stanyOstrzegawcze = {}
        stanyAlarmowe = {}

        zaladowaneRegiony = []
        self.zaladujWybraneWodowskazy()

        if self._dane_wodowskazow:
            for wodowskaz in self.__wodowskazy:
                region = wodowskaz.split(".")[0]

                if region not in zaladowaneRegiony:
                    zaladowaneRegiony.append(region)
                    # w = s.pobierzDaneWodowskazu(wodowskaz)
                try:
                    w = self.pobierzDaneWodowskazu(wodowskaz)
                    rzeka = w["rzeka"]
                    w["rzeka"] = self.safe_name(w["rzeka"])
                    w["nazwa"] = self.safe_name(w["nazwa"])

                    id_wodowskazu = wodowskaz + " - " + rzeka + " - " + w["nazwa_org"]
                    tendencja = w["nazwa"] + " " + w["tendencja"] + " _ "
                    if w["przekroczenieStanu"] == "ostrzegawczy":
                        self.__logger.info("::: Stan ostrzegawczy: %s", id_wodowskazu)
                        if w["rzeka"] not in stanyOstrzegawcze:
                            stanyOstrzegawcze[w["rzeka"]] = [tendencja]

                        else:
                            stanyOstrzegawcze[w["rzeka"]].append(tendencja)

                    elif w["przekroczenieStanu"] == "alarmowy":
                        self.__logger.info("::: Stan alarmowy: %s", id_wodowskazu)
                        if w["rzeka"] not in stanyAlarmowe:
                            stanyAlarmowe[w["rzeka"]] = [tendencja]

                        else:
                            stanyAlarmowe[w["rzeka"]].append(tendencja)

                    else:
                        self.__logger.debug("Przetwarzam wodowskaz: %s", id_wodowskazu)
                except KeyError:
                    self.__logger.exception(
                        "::: Brak danych dla wodowskazu %s!!! ", wodowskaz
                    )

            message = ["_", "_"]
            if stanyOstrzegawcze != {} or stanyAlarmowe != {}:
                message.append("komunikat_hydrologiczny_imgw")
                message.append("_")

                if stanyAlarmowe != {}:
                    # Sprawdzenie dla których wodowskazów mamy przekroczone
                    # stany alarmowe -- włącz ctcss

                    message.append("przekroczenia_stanow_alarmowych")
                    for rzeka in sorted(stanyAlarmowe.keys()):
                        message.append("rzeka")
                        message.append(rzeka)
                        for wodowskaz in sorted(stanyAlarmowe[rzeka]):
                            message.append("wodowskaz")
                            message.append(wodowskaz)

                if stanyOstrzegawcze != {}:
                    message.append("_")
                    message.append("przekroczenia_stanow_ostrzegawczych")
                    for rzeka in sorted(stanyOstrzegawcze.keys()):
                        message.append("rzeka")
                        message.append(rzeka)
                        for wodowskaz in sorted(stanyOstrzegawcze[rzeka]):
                            message.append("wodowskaz")
                            message.append(format(wodowskaz))

            self.__logger.info("::: Przekazuję przetworzone dane...\n")

            message.append("_")

        return {
            "message": message,
            "source": "imgw",
        }


def create(config):
    return ImgwPodestSq9atk(**config)
