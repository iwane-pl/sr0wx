#!/usr/bin/python -tt
#
#
# ********
# sr0wx.py
# ********
#
# This is main program file for automatic weather station project;
# codename SR0WX.
#
# (At the moment) SR0WX can read METAR [#]_ weather informations and
# is able to read them aloud in Polish. SR0WX is fully extensible, so
# it's easy to make it read any other data in any language (I hope).
#
# .. [#] http://en.wikipedia.org/wiki/METAR
#
# =====
# About
# =====
#
# Every automatic station's callsign in Poland (SP) is prefixed by "SR".
# This software is intended to read aloud weather informations (mainly).
# That's why we (or I) called it SR0WX.
#
# Extensions (mentioned above) are called ``modules`` (or ``languages``).
# Main part of SR0WX is called ``core``.
#
# SR0WX consists quite a lot of independent files so I (SQ6JNX) suggest
# reading other manuals (mainly configuration- and internationalization
# manual) in the same time as reading this one. Really.
# ============
# Requirements
# ============
#
# SR0WX (core) requires the following packages:

import contextlib
import importlib
import os
import pygame
import logging, logging.handlers
import logging.config
import numpy
import urllib.request, urllib.error, urllib.parse
import socket

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import argparse
from colorama import Fore, Style

from hw.ptt import PTT

# ``os``, ``sys`` and ``time`` doesn't need further explanation, these are
# standard Python packages.
#
# ``pygame`` [#]_ is a library helpful for game development, this project
# uses it for reading (playing) sound samples. ``config`` is just a
# SR0WX configuration file, and it is described separately.
#
# ..[#] www.pygame.org

COLOR_HEADER = Fore.LIGHTMAGENTA_EX
COLOR_OKBLUE = Fore.BLUE
COLOR_OKGREEN = Fore.GREEN
COLOR_WARNING = Fore.YELLOW
COLOR_FAIL = Fore.RED
COLOR_BOLD = Style.BRIGHT
COLOR_UNDERLINE = '\033[4m'
COLOR_ENDC = Style.RESET_ALL

LICENSE = """

Copyright 2009-2014 Michal Sadowski (sq6jnx at hamradio dot pl)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

-----------------------------------------------------------

You can find full list of contributors on github.com/sq6jnx/sr0wx.py

"""

DATA_SOURCES_ERROR_MSG = ['_', 'zrodlo_danych_niedostepne']
HELLO_MSG = ['_', 'tu_eksperymentalna_automatyczna_stacja_pogodowa', 'sr0wx']
GOODBYE_MSG = ['_', 'tu_sr0wx']


#
#
# =========
# Let's go!
# =========
#
# For information purposes script says hello and gives local time/date,
# so it will be possible to find out how long script was running.

# Logging configuration
def setup_logging(config, debug=False):
    config['version'] = 1
    # TODO: delete when module is refactored to load plugins after setup
    config['disable_existing_loggers'] = False
    logging.config.dictConfig(config)
    logger = logging.getLogger()
    if debug:
        logger.setLevel(logging.DEBUG)
        for hnd in logger.handlers:
            hnd.setLevel(logging.DEBUG)

    return logger

# All datas returned by SR0WX modules will be stored in ``data`` variable.

# Information about which modules are to be executed is written in SR0WX
# config file. Program starts every single of them and appends its return
# value in ``data`` variable. As you can see every module is started with
# language variable, which is also defined in configuration.
# Refer configuration and internationalization manuals for further
# information.
#
# Modules may be also given in commandline, separated by a comma.

cfg_data = None


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to an alternate config.toml file")
    parser.add_argument("-d", "--debug", action='store_true', help="Enable debug logging")
    parser.add_argument("-t", "--test-mode", action='store_true',
                        help="Enable test mode (disables serial port operations)")
    parser.add_argument("modules", metavar='MOD', nargs='*', help="Limit modules to use")
    args = parser.parse_args()
    return args


def test_internet_connection():
    try:
        urllib.request.urlopen('http://google.pl', None, 30)
        return True
    except (urllib.error.URLError, socket.error, socket.timeout):
        return False


def collect_messages(modules):
    message = []
    sources = []
    for module in modules:
        try:
            logger.info(f"{COLOR_OKGREEN}starting %s...{COLOR_ENDC}", module)
            module_data = module.get_data()
            module_message = module_data.get("message", "")
            module_source = module_data.get("source", "")

            message.extend(module_message)
            if module_message != "" and module_source != "":
                sources.append(module_data['source'])
        except Exception:
            logger.exception(f"{COLOR_FAIL}Exception when running %s{COLOR_ENDC}", module)
    return message, sources


def play_ctcss(freq, volume):
    volume = volume * 1000
    sampling_freq = cfg_data['playback']['sampling_frequency']
    arr = numpy.array([volume * numpy.sin(2.0 * numpy.pi * round(freq) * x / sampling_freq) for x in
                       range(0, sampling_freq)]).astype(numpy.int16)
    arr2 = numpy.c_[arr, arr]
    ctcss = pygame.sndarray.make_sound(arr2)
    logger.info(f"{COLOR_WARNING}Playing CTCSS tone %.1fHz{COLOR_ENDC}\n", freq)
    ctcss.play(-1)


def prepare_sample_dictionary():
    sound_samples = {}
    for el in message:
        if isinstance(el, str):
            if el.startswith('file://'):
                sound_samples[el] = pygame.mixer.Sound(el.removeprefix("file://"))

            if el != "_" and el not in sound_samples:
                sample_path = os.path.join("assets", cfg_data['options']['language'], f"{el}.ogg")
                if not os.path.isfile(sample_path):
                    logger.warning(f"{COLOR_FAIL}Couldn't find %s{COLOR_ENDC}", sample_path)
                    sound_samples[el] = pygame.mixer.Sound(
                        os.path.join("assets", cfg_data['options']['language'], "beep.ogg"))
                else:
                    sound_samples[el] = pygame.mixer.Sound(sample_path)
        else:
            logger.error("Unsupported sample type: %s (sample %s)", type(el), el)
    return sound_samples


if __name__ == "__main__":
    message = []
    args = parse_args()

    config_toml_path = 'config.toml'
    if args.config:
        config_toml_path = args.config

    with open(config_toml_path, 'rb') as f:
        cfg_data = tomllib.load(f)

    logger = setup_logging(cfg_data['log'], debug=args.debug)

    logger.info(f"{COLOR_WARNING}sr0wx.py started{COLOR_ENDC}")
    logger.info(f"{Fore.BLUE}{LICENSE}{Style.RESET_ALL}")

    ptt = PTT(cfg_data['serial']['port'],
              cfg_data['serial']['baudrate'],
              cfg_data['serial']['ptt_signal'],
              args.test_mode,
              )

    lang_module = importlib.import_module(f"speech.{cfg_data['options']['language']}")

    modules = []
    for name, plugin_config in cfg_data['plugins'].items():
        if plugin_config['enabled']:
            # import and configure plugin module
            m = importlib.import_module(f"plugins.{name}")
            combined_config = cfg_data['location'].copy()
            combined_config['language'] = lang_module
            combined_config.update(plugin_config)
            plugin = m.create(combined_config)
            modules.append(plugin)

    logger.debug("Loaded modules: %s", modules)
    if args.modules:
        modules = [m for m in modules if m.__module__ in args.modules]
    logger.debug("Used modules: %s", modules)

    is_connected = test_internet_connection()
    if not is_connected:
        modules = []
        message.extend(DATA_SOURCES_ERROR_MSG)
        logger.error(f"{COLOR_FAIL}No internet connection{COLOR_ENDC}\n")

    # sources = []
    # lang = my_import('.'.join((config.lang, config.lang)))
    # sources = [lang.source, ]

    message, sources = collect_messages(modules)

    # When all the modules finished its work it's time to ``.split()`` returned
    # data. Every element of returned list is actually a filename of a sample.

    message = HELLO_MSG + message
    if cfg_data['playback']['read_sources']:
        if len(sources) > 1:
            message.extend(sources)
    else:
        message.extend( sources )
    message.extend(GOODBYE_MSG)

    # It's time to init ``pygame``'s mixer (and ``pygame``).

    pygame.mixer.init(cfg_data['playback']['sampling_frequency'], -16, 2, 1024)

    # Next (as a tiny timesaver & memory eater ;) program loads all necessary
    # samples into memory. I think that this is better approach than reading
    # every single sample from disk in the same moment when it's time to play it.

    # Just for debug: our playlist (whole message as a list of filenames)

    playlist = []

    for el in message:
        if isinstance(el, str):
            playlist.append(el)
        else:
            playlist.append("[sndarray]")

    if 'ctcss' in cfg_data:
        play_ctcss(cfg_data['ctcss']['tone'], cfg_data['ctcss']['volume'])

    logger.info("playlist elements: %s", " ".join(playlist) + "\n")
    logger.info("loading sound samples...")

    sound_samples = prepare_sample_dictionary()

    # Program should be able to "press PTT" via RSS232. See ``config`` for
    # details.

    ptt.press()

    pygame.time.delay(1000)

    # OK, data prepared, samples loaded, let the party begin!
    #
    # Take a look at ``while`` condition -- program doesn't check if the
    # sound had finished played all the time, but only 25 times/sec (default).
    # It is because I don't want 100% CPU usage. If you don't have as fast CPU
    # as mine (I think you have, though) you can always lower this value.
    # Unfortunately, there may be some pauses between samples so "reading
    # aloud" will be less natural.

    logger.info("playing sound samples\n")
    voice_channel = None
    for el in message:
        # print el # wyświetlanie nazw próbek
        logger.debug("Sample: %s", el)
        if el == "_":
            # pause
            pygame.time.wait(500)
        else:
            if isinstance(el, str):
                # sample name
                with contextlib.suppress(Exception):
                    voice_channel = sound_samples[el].play()
            elif isinstance(el, numpy.ndarray):
                # sample in an array form
                sound = pygame.sndarray.make_sound(el)
                if config.pygame_bug == 1:
                    sound = pygame.sndarray.make_sound(
                        pygame.sndarray.array(sound)[:len(pygame.sndarray.array(sound)) / 2])
                voice_channel = sound.play()
            else:
                logger.error("Unsupported sample type: %s (sample %s)", type(el), el)

            if voice_channel:
                # wait until playback finishes
                while voice_channel.get_busy():
                    pygame.time.Clock().tick(25)

    # Possibly the argument of ``pygame.time.Clock().tick()`` should be in
    # config file...
    #
    # The following four lines give us a one second break (for CTCSS, PTT and
    # other stuff) before closing the ``pygame`` mixer and display some debug
    # informations.

    logger.info(f"{COLOR_WARNING}finishing in 1 second...\n{COLOR_ENDC}")

    pygame.time.delay(1000)

    ptt.release()

    logger.info(f"{COLOR_WARNING}goodbye{COLOR_ENDC}")

    # Documentation is a good thing when you need to double or triple your
    # Lines-Of-Code index ;)
