#!/usr/bin/python -tt
import datetime
import logging
import os.path
from typing import Iterable

import msgspec
import requests

from sr0wx_module import SR0WXModule


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


# data schemas for deserialization
class WGWaterState(msgspec.Struct):
    date: datetime.datetime
    value: float


class WGStatus(msgspec.Struct):
    river: str
    currentState: WGWaterState
    previousState: WGWaterState
    outdatedState: bool
    description: str
    province: str

    @property
    def river_name(self):
        return self.river.split("(")[0].strip()


class WGData(msgspec.Struct):
    id: int
    status: WGStatus
    alarmValue: float
    warningValue: float
    trend: str
    name: str

    @property
    def has_alarm(self):
        return self.status.currentState.value > self.alarmValue

    @property
    def has_warning(self):
        return self.status.currentState.value > self.warningValue


# TODO: tests - as there are data on disk
class ImgwPodestSq9atk(SR0WXModule):
    """Klasa przetwarza dane informujące o przekroczeniach stanów rzek w regionie."""

    TRENDS = {
        "up": "tendencja_wzrostowa",
        "down": "tendencja_spadkowa",
    }

    def __init__(self, service_url: str, water_gauges: Iterable[int], **kwargs):
        super().__init__()
        self.__logger = logging.getLogger(__name__)
        self._service_url = service_url
        self._selected_water_gauges = water_gauges
        # debug mode, loads data from disk
        self._offline: bool = kwargs.pop("offline_mode", False)
        if self._offline:
            self.__logger.info("Debug mode: IMGW data loaded from disk!")
        self._wg_data: dict[int, WGData | None] = {}

    def load_wg_data(self):
        self.__logger.info("::: Downloading water gauge data...")
        for wg in self._selected_water_gauges:
            self._wg_data[wg] = None
            try:
                self.__logger.debug("Water gauge ID: %s", wg)
                if not self._offline:
                    resp = requests.request("GET", self._service_url.format(wg))
                    resp.raise_for_status()
                    # strict=False to allow automatic gauge ID conversion from str
                    self._wg_data[wg] = msgspec.json.decode(
                        resp.content, type=WGData, strict=False
                    )
                else:
                    with open(
                        os.path.join("test", "data", f"test_{wg}_map.json"),
                        encoding="utf-8",
                    ) as f:
                        self._wg_data[wg] = msgspec.json.decode(
                            f.read(), type=WGData, strict=False
                        )

            except requests.exceptions.HTTPError:
                self.__logger.exception("Couldn't download water gauge %s data", wg)
                raise
            except OSError:
                self.__logger.exception("Couldn't load data from disk")
                raise
            except msgspec.ValidationError:
                self.__logger.exception("There is an error in received data")
                raise

    def get_data(self):
        message = ["_", "_"]
        warning_states = {}
        alarm_states = {}

        self.load_wg_data()

        if self._wg_data:
            for wg_id in self._selected_water_gauges:
                try:
                    w = self._wg_data[wg_id]
                    river = w.status.river_name
                    river_sample = self.safe_name(river)
                    wg_name_sample = self.safe_name(w.name.lower())

                    wg_id_for_log = f"{wg_id} - {river} - {w.name}"
                    trend_samples = [
                        wg_name_sample,
                        self.TRENDS.get(w.trend, "beep"),
                        "_",
                    ]
                    if w.has_alarm:
                        self.__logger.info("::: Alarm state: %s", wg_id_for_log)
                        if river_sample not in alarm_states:
                            alarm_states[river_sample] = [trend_samples]

                        else:
                            alarm_states[river_sample].append(trend_samples)

                    elif w.has_warning:
                        self.__logger.info("::: Warning state: %s", wg_id_for_log)
                        if river_sample not in warning_states:
                            warning_states[river_sample] = [trend_samples]

                        else:
                            warning_states[river_sample].append(trend_samples)
                    else:
                        self.__logger.debug("Parsed water gauge: %s", wg_id_for_log)
                except KeyError:
                    self.__logger.exception("::: No data for water gauge %s!!! ", wg_id)

            if warning_states != {} or alarm_states != {}:
                message.append("komunikat_hydrologiczny_imgw")
                message.append("_")

                if alarm_states != {}:
                    # Sprawdzenie dla których wodowskazów mamy przekroczone
                    # stany alarmowe -- włącz ctcss

                    message.append("przekroczenia_stanow_alarmowych")
                    for river in sorted(alarm_states.keys()):
                        message.append("rzeka")
                        message.append(river)
                        for wg in sorted(alarm_states[river]):
                            message.append("wodowskaz")
                            message.extend(wg)

                if warning_states != {}:
                    message.append("_")
                    message.append("przekroczenia_stanow_ostrzegawczych")
                    for river in sorted(warning_states.keys()):
                        message.append("rzeka")
                        message.append(river)
                        for wg in sorted(warning_states[river]):
                            message.append("wodowskaz")
                            message.extend(wg)

            self.__logger.info("::: Finished parsing water gauge data...\n")

            message.append("_")

        return {
            "message": message,
            "source": "imgw",
        }


def create(config):
    return ImgwPodestSq9atk(**config)
