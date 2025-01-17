#!/usr/env/python -tt
# -*- encoding=utf8 -*-
#
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

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import BeautifulSoup

from . import debug

lang = None


def safe_name(s):
    """Returns "safe" name for i.e. geographical name for languages with
    non-latin characters i.e. polish, where there are boty Ślęża and Ślęza
    rivers (both are usually converted to Sleza, but should be read aloud
    differently.

    I've no idea if such situation appears in czech, but... just in case..."""

    if str(s.__class__) == "<type 'str'>":
        s = str(s, "utf-8")
    return (
        s.replace("á", "a_")
        .replace("é", "e_")
        .replace("ě", "e!")
        .replace("í", "i_")
        .replace("ó", "o_")
        .replace("ú", "o!")
        .replace("ů", "u_")
        .replace("ý", "y_")
        .replace("ď", "d_")
        .replace("ť", "t_")
        .replace("ň", "n_")
        .replace("ř", "r_")
        .replace("š", "s_")
        .replace("č", "c_")
        .replace("ž", "z_")
        .replace("Á", "a_")
        .replace("É", "e_")
        .replace("Ě", "e!")
        .replace("Í", "i_")
        .replace("Ó", "o_")
        .replace("Ú", "o!")
        .replace("Ů", "u_")
        .replace("Ý", "y_")
        .replace("Ď", "d_")
        .replace("Ť", "t_")
        .replace("Ň", "n_")
        .replace("Ř", "r_")
        .replace("Š", "s_")
        .replace("Č", "c_")
        .replace("Ž", "z_")
        .lower()
        .replace(" ", "_")
        .replace("–", "_")
    )


def downloadFile(url):
    webFile = urllib.request.urlopen(url)
    return webFile.read()


def my_import(name):
    mod = __import__(name)
    components = name.split(".")
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def getData(lang_module):
    data = {
        "data": "",
        "needCTCSS": False,
        "allOK": True,
        "source": "",
    }  # given by welcome message

    regions = get_config_regions()

    if not os.path.exists("povodi_cz.json"):
        regions = generate_json(regions=list(regions.keys()), dont_save=False)
    else:
        regions = json.loads(str(open("povodi_cz.json", "r").read(), "utf-8"))

    awarenesses = {}

    for region in list(regions.keys()):
        for river in regions[region]:
            for station in list(regions[region][river].keys()):
                station_name, level = regions[region][river][station]
                if [region, station] in config.stations and level > 0:
                    if str(level) not in awarenesses:
                        awarenesses[str(level)] = {}
                    if safe_name(river) not in awarenesses[str(level)]:
                        awarenesses[str(level)][safe_name(river)] = []
                    awarenesses[str(level)][safe_name(river)].append(
                        safe_name(regions[region][river][station][0])
                    )

    awalvls = [
        "",
        "stopien_czuwania",
        "stopien_gotowosci",
        "stopien_zagrozenia",
        "stopien_ekstremalnych_powodzi",
    ]

    if awarenesses != {}:
        data[
            "data"
        ] += "komunikat_hydrologiczny_czeskiego_instytutu_hydrometeorologicznego"
        for level in sorted(awarenesses.keys())[::-1]:
            if level > 1:
                data["needCTCSS"] = True
            data["data"] += " " + awalvls[int(level)]
            for river in sorted(awarenesses[level].keys()):
                data["data"] += " " + "rzeka" + " " + river
                for station in sorted(awarenesses[level][river]):
                    data["data"] += " " + "wodowskaz" + " " + station

    if os.path.exists("povodi_cz.json"):
        os.remove("povodi_cz.json")

    debug.log("POVODI_CZ", "finished...")
    return data


def show_help():
    print(
        """
Uruchamiając ten skrypt z linii komend możesz wygenerować w łatwy sposób 
fragment słownika sr0wx dla rzek i wodowskazów wskazanych w pliku config.py

Należy uruchomić povodi_cz podając jako parametr gen, np.

python povodi_cz.py gen > pl_google/povodi_cz_dict.py

a następnie

python google_tts_downloader.py povodi_cz_dict.py

aby dociągnąć niezbędne pliki."""
    )


def get_region(region):
    """Returns dictionary with all rivers and stations with flood awareness
    levels on these stations.

    This dictionary is constructed as: ::

        rv[river][(station_id, station)]=awareness_level
    """

    url = "http://www.%s.cz/portal/sap/en/mapa_%s.htm"
    region, _map = region[0:3], region[3]
    # print url%(region,_map)

    # there are moments in a turtle's life that a turtle has
    # to smack someone's face:
    html_file = (
        downloadFile(url % (region, _map))
        .replace("-href", "href")
        .replace("chaset", "charset")
    )

    html = BeautifulSoup.BeautifulSoup(html_file)
    rv = {}
    river = None

    # try:
    if 1 == 1:
        for station in html.findAll("div"):
            if "id" in station and "text" in station["id"]:
                r1, r2 = station.findAll("table")
                stid = station["id"][4:]  # station id
                river = str(
                    r1.findAll("tr")[0].findAll("td")[0].findAll("font")[0]
                ).split("&nbsp;")[1][0:-7]

                station = str(
                    r1.findAll("tr")[0].findAll("td")[0].findAll("font")[1]
                ).split("&nbsp;")[1][0:-7]
                station = station.replace("LG ", "")

                try:
                    if "Chyba" in str(r1.findAll("tr")[1].findAll("tr")[0]):
                        level = "-2"
                    elif "Porucha" in str(r1.findAll("tr")[1].findAll("tr")[0]):
                        level = "-1"
                    elif "porucha" in str(r1.findAll("tr")[1].findAll("tr")[0]):
                        level = "-1"
                    elif "ledem" in str(r1.findAll("tr")[1].findAll("tr")[0]):
                        level = "-1"
                    else:
                        level = str(
                            r1.findAll("tr")[1]
                            .findAll("tr")[0]
                            .findAll("font")[0]
                            .findAll("b")[0]
                        )[3:-4]
                except Exception:
                    debug.log(
                        "POVODI_CZ",
                        str(r1.findAll("tr")[1].findAll("tr")[0]),
                        buglevel=5,
                    )

                if level == "":
                    level = 0
                elif level == "?":
                    level = -1
                else:
                    level = int(level)

                # print '|'.join( (region,_map, str(stid),river, station, level) )

                if river not in rv:
                    rv[river] = {}
                rv[river][stid] = [station, level]
                # debug trick: WE are steering water levels
                # from random import uniform
                # level = int(uniform(1,5))
                # rv[river][stid]=[station, int(uniform(1,5))]
                # end of trick
    # except:
    else:
        debug.log(
            "POVODI_CZ", "Couldn't parse region %s%s data" % (region, _map), buglevel=5
        )
        pass

    return rv


def generate_json(regions=None, dont_save=False):
    """Generates povodi_cz.json file and returns its contents (dictionary).

    This file contains all river stations and the way it's constructed is: ::

        rv[region][river][station]=awareness_level
    """
    rv = {}
    if regions is None:
        regions = [
            "poh1",
            "poh2",
            "poh3",
            "pla1",
            "pla2",
            "pla3",
            "pla4",
            "pla5",
            "pod1",
            "pod2",
            "pmo1",
            "pmo2",
            "pmo3",
            "pvl1",
            "pvl2",
            "pvl3",
        ]

    for region in regions:
        # try:
        if 1 == 1:
            rv[region] = get_region(region)
        # except:
        else:
            debug.log(
                "POVODI_CZ", "Couldn't download data for region %s" % region, buglevel=5
            )
            pass

    if not dont_save:
        json.dump(rv, open("povodi_cz.json", "w"))

    return rv


def generate_config():
    regions = generate_json(dont_save=True)

    print("povodi_cz.stations = [")

    for region in sorted(regions.keys()):
        for river in sorted(regions[region].keys()):
            for station in sorted(regions[region][river].keys()):
                print(
                    "    ['%s','%s'],\t# %s, station %s"
                    % (
                        region,
                        station,
                        str(river, "utf-8"),
                        str(regions[region][river][station][0], "utf-8"),
                    )
                )
    print("]")


def get_config_regions():
    regions = {}
    for station in config.stations:
        if station[0] not in regions:
            regions[station[0]] = []
        regions[station[0]].append(station[1])
    return regions


def generate_dictionary():
    regions = get_config_regions()

    phrases = []
    for region in list(regions.keys()):
        region_data = get_region(region)
        for river in sorted(region_data.keys()):
            for station in sorted(region_data[river].keys()):
                if (
                    station in regions[region]
                    and region_data[river][station][0] not in phrases
                ):
                    phrases.append(region_data[river][station][0])
                    if river not in phrases:
                        phrases.append(river)

    print(
        """#!/usr/bin/python
# -*- coding: utf-8 -*-

# Caution! I am not responsible for using these samples. Use at your own risk
# Google, Inc. is the copyright holder of samples downloaded with this tool.

# Generated automatically by povodi_cz.py. Feel free to modify it SLIGHTLY.

LANGUAGE = 'cs'

START_MARKER = '@'
END_MARKER = '@'

CUT_START = 0.9
CUT_END=0.7

download_list = [ """
    )

    for phrase in phrases:
        print(
            '    ["%s", "%s"], # %s'
            % (str(phrase, "utf-8"), safe_name(phrase), str(phrase, "utf-8"))
        )

    print("]")


if __name__ == "__main__":

    class DummyDebug:
        def log(self, module, message, buglevel=None):
            print(message)

    # debug = DummyDebug()
    import sys

    # I know it would be better to use getopt or similar, but is there a point
    # for using such a moloch for barely two options?

    if len(sys.argv) == 2 and sys.argv[1] == "dict":
        from config import povodi_cz as config

        generate_dictionary()
    elif len(sys.argv) == 2 and sys.argv[1] == "conf":
        generate_config()
    elif len(sys.argv) == 2 and sys.argv[1] == "json":
        generate_json()
    # else:
    #    #show_help()
else:
    from config import povodi_cz as config
