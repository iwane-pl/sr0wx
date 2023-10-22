#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

# AKTUALNIE ZALECANE JEST UBUNTU 16.04 MATE
# Poniższy opis dotyczy tej dystrybucji

# WYMAGANE DODATKOWE PAKIETY:
#   sudo apt-get install git
#   sudo apt-get install python-pygame
#   sudo apt-get install python-tz
#   sudo apt-get install python-imaging
#   sudo apt-get install python-serial
#   sudo apt-get install python-six
#   sudo apt-get install curl
#   sudo apt-get install php7.0
#   sudo apt-get install php7.0-curl
#   sudo apt-get install php7.0-xml
#   sudo apt-get install ffmpeg
#
# LUB WSZYSTKO NA RAZ
#   sudo apt-get install git python-pygame python-tz python-imaging python-serial python-six curl php7.0 php7.0-curl php7.0-xml ffmpeg

# UPRAWNIENIA USERA DO PORTU COM
#   sudo gpasswd --add ${USER} dialout

# GENEROWANIE SAMPLI
# Będąc w katalogu audio_generator:
#   php index.php
#
# Generowane są sample z tablicy $słownik z pliku slownik.php.
# Pozostałe tablice to tylko przechowalnia fraz go wygenerowania.



data_sources_error_msg = ['_', 'zrodlo_danych_niedostepne']
hello_msg = ['_', 'tu_eksperymentalna_automatyczna_stacja_pogodowa', 'sr0wx']
goodbye_msg = ['_', 'tu_sr0wx']
read_sources_msg = False
