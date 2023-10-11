#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
import argparse

COLOR_HEADER = '\033[95m'
COLOR_OKBLUE = '\033[94m'
COLOR_OKGREEN = '\033[92m'
COLOR_WARNING = '\033[93m'
COLOR_FAIL = '\033[91m'
COLOR_BOLD = '\033[1m'
COLOR_UNDERLINE = '\033[4m'
COLOR_ENDC = '\033[0m'

LICENSE = COLOR_OKBLUE + """

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

""" + COLOR_ENDC

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
#
# ============
# Requirements
# ============
#
# SR0WX (core) requires the following packages:

import contextlib
import os
import pygame
import logging, logging.handlers
import numpy
import urllib.request, urllib.error, urllib.parse
import socket


# ``os``, ``sys`` and ``time`` doesn't need further explanation, these are
# syandard Python packages.
#
# ``pygame`` [#]_ is a library helpful for game development, this project
# uses it for reading (playing) sound samples. ``config`` is just a
# SR0WX configuration file, and it is described separately.
#
# ..[#] www.pygame.org
#
# =========
# Let's go!
# =========
#
# For information purposes script says hello and gives local time/date,
# so it will be possible to find out how long script was running.

# Logging configuration
def setup_logging(config, debug=False):
    # create formatter and add it to the handlers
    formatter = logging.Formatter(config.log_line_format)

    # Creating logger with the lowest log level in config handlers
    min_log_level = logging.DEBUG if debug else min([h['log_level'] for h in config.log_handlers])
    logger = logging.getLogger()
    logger.setLevel(min_log_level)

    # create logging handlers according to its definitions
    for handler_definition in config.log_handlers:
        handler = handler_definition['class'](**handler_definition['config'])
        handler.setLevel(logging.DEBUG if debug else handler_definition['log_level'])
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


#
# All datas returned by SR0WX modules will be stored in ``data`` variable.

message = " "

# Information about which modules are to be executed is written in SR0WX
# config file. Program starts every single of them and appends its return
# value in ``data`` variable. As you can see every module is started with
# language variable, which is also defined in configuration.
# Refer configuration and internationalization manuals for further
# information.
#
# Modules may be also given in commandline, separated by a comma.

config = None


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    parser.add_argument("-d", "--debug", action='store_true')
    parser.add_argument("-t", "--test-mode", action='store_true')
    parser.add_argument("modules", metavar='MOD', nargs='*')
    args = parser.parse_args()
    return args


def test_internet_connection():
    try:
        urllib.request.urlopen('http://google.pl', None, 30)
        return True
    except (urllib.error.URLError, socket.error, socket.timeout):
        return False


def collect_messages(modules):
    message = " "
    for module in modules:
        try:
            logger.info(COLOR_OKGREEN + "starting %s..." + COLOR_ENDC, module)
            module_data = module.get_data()
            module_message = module_data.get("message", "")
            module_source = module_data.get("source", "")

            message = " ".join((message, module_message))
            if module_message != "" and module_source != "":
                sources.append(module_data['source'])
        except Exception:
            logger.exception(COLOR_FAIL + "Exception when running %s" + COLOR_ENDC, module)
    return message


def play_ctcss(freq):
    volume = 25000
    arr = numpy.array([volume * numpy.sin(2.0 * numpy.pi * round(freq) * x / 16000) for x in
                       range(0, 16000)]).astype(numpy.int16)
    arr2 = numpy.c_[arr, arr]
    ctcss = pygame.sndarray.make_sound(arr2)
    logger.info(COLOR_WARNING + "CTCSS tone %.1fHz" + COLOR_ENDC + "\n", freq)
    ctcss.play(-1)


def prepare_sample_dictionary():
    sound_samples = {}
    for el in message:
        if isinstance(el, str):
            if el[0:7] == 'file://':
                sound_samples[el] = pygame.mixer.Sound(el[7:])

            if el != "_" and el not in sound_samples:
                if not os.path.isfile(config.lang + "/" + el + ".ogg"):
                    logger.warn(COLOR_FAIL + "Couldn't find %s" % (config.lang + "/" + el + ".ogg" + COLOR_ENDC))
                    sound_samples[el] = pygame.mixer.Sound(config.lang + "/beep.ogg")
                else:
                    sound_samples[el] = pygame.mixer.Sound(config.lang + "/" + el + ".ogg")
        else:
            logger.error("Unsupported sample type: %s (sample %s)", type(el), el)
    return sound_samples

# TODO: make it a class
ser = None
def press_ptt():
    global ser
    import serial
    try:
        ser = serial.Serial(config.serial_port, config.serial_baud_rate)
        if config.serial_signal == 'DTR':
            logger.info(COLOR_OKGREEN + "DTR/PTT set to ON\n" + COLOR_ENDC)
            ser.dtr = True
            ser.rts = False
        else:
            logger.info(COLOR_OKGREEN + "RTS/PTT set to ON\n" + COLOR_ENDC)
            ser.dtr = False
            ser.rts = True
    except serial.SerialException:
        log = COLOR_FAIL + "Failed to open serial port %s@%i\n" + COLOR_ENDC
        logger.error(log, config.serial_port, config.serial_baud_rate)


def release_ptt():
    # If we've opened serial it's now time to close it.
    try:
        if not args.test_mode and config.serial_port is not None:
            ser.close()
            logger.info(COLOR_OKGREEN + "RTS/PTT set to OFF\n" + COLOR_ENDC)
    except NameError:
        # sudo gpasswd --add ${USER} dialout
        logger.exception(COLOR_FAIL + "Couldn't close serial port" + COLOR_ENDC)


if __name__ == "__main__":
    args = parse_args()

    if args.config:
        config = __import__(os.path.splitext(args.config)[0])
    if config is None:
        import config

    logger = setup_logging(config, debug=args.debug)

    logger.info(COLOR_WARNING + "sr0wx.py started" + COLOR_ENDC)
    logger.info(LICENSE)
    if args.test_mode:
        logger.info("Test mode enabled, skipping serial port usage")

    modules = config.modules
    logger.debug("Załadowane moduły: %s", modules)
    if args.modules:
        modules = [m for m in modules if m.__module__ in args.modules]
    logger.debug("Używane moduły: %s", modules)

    is_connected = test_internet_connection()
    if not is_connected:
        modules = []
        message += " ".join(config.data_sources_error_msg)
        logger.error(COLOR_FAIL + "Brak połączenia z internetem" + COLOR_ENDC + "\n")

    lang = my_import('.'.join((config.lang, config.lang)))
    sources = [lang.source, ]

    message = collect_messages(modules)

    # When all the modules finished its work it's time to ``.split()`` returned
    # data. Every element of returned list is actually a filename of a sample.

    message = config.hello_msg + message.split()
    if hasattr(config, 'read_sources_msg'):
        if config.read_sources_msg:
            if len(sources) > 1:
                message += sources
    else:
        message += sources
    message += config.goodbye_msg

    # It's time to init ``pygame``'s mixer (and ``pygame``). Possibly defined
    # sound quality is far-too-good (44kHz 16bit, stereo), so you can change it.

    pygame.mixer.init(16000, -16, 2, 1024)

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

    if hasattr(config, 'ctcss_tone'):
        play_ctcss(config.ctcss_tone)

    logger.info("playlist elements: %s", " ".join(playlist) + "\n")
    logger.info("loading sound samples...")
    logger.info("playing sound samples\n")

    sound_samples = prepare_sample_dictionary()

    # Program should be able to "press PTT" via RSS232. See ``config`` for
    # details.

    if not args.test_mode and config.serial_port is not None:
        press_ptt()

    pygame.time.delay(1000)

    # OK, data prepared, samples loaded, let the party begin!
    #
    # Take a look at ``while`` condition -- program doesn't check if the
    # sound had finished played all the time, but only 25 times/sec (default).
    # It is because I don't want 100% CPU usage. If you don't have as fast CPU
    # as mine (I think you have, though) you can always lower this value.
    # Unfortunately, there may be some pauses between samples so "reading
    # aloud" will be less natural.

    for el in message:
        # print el # wyświetlanie nazw próbek
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
            while voice_channel.get_busy():
                pygame.time.Clock().tick(25)

    # Possibly the argument of ``pygame.time.Clock().tick()`` should be in
    # config file...
    #
    # The following four lines give us a one second break (for CTCSS, PTT and
    # other stuff) before closing the ``pygame`` mixer and display some debug
    # informations.

    logger.info(COLOR_WARNING + "finishing...\n" + COLOR_ENDC)

    pygame.time.delay(1000)

    release_ptt()

    logger.info(COLOR_WARNING + "goodbye" + COLOR_ENDC)

    # Documentation is a good thing when you need to double or triple your
    # Lines-Of-Code index ;)
