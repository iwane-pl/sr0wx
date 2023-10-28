# sr0wx

This is a fork of [sq9atk/sr0wx](https://github.com/sq9atk/sr0wx) ported to Python 3.
I'm working on Python 3.11 currently, and basic functionality works on it.

`sr0wx` is an automatic weather station software with audio announcement. It's meant for transmission
of the weather message through the amateur radio transmitter, though it can be easily used in other
situations.

For more information on SR0WX project, see https://ostol.pl/stacja-pogodowa-sr0wx-py (Only Polish for now, sorry)

## Supported languages

- Polish (for now)

## Supported data sources

* [OpenWeatherMap](https://openweathermap.org)
    * OpenWeatherMap needs an API key for Free plan (60 API calls per minute, which is more than enough)
* [GIOS](https://powietrze.gios.gov.pl/pjp/home) (air pollution - Chief Inspectorate For Environmental Protection)
    * GIOŚ has a free [API](https://powietrze.gios.gov.pl/pjp/content/api) with limits enough for getting data
* Airly (air pollution)
    * Airly needs an API key from https://developer.airly.org/
* GisMeteo (geomagnetic data)
    * **Disabled by default**, as [GisMeteo ToS](https://www.gismeteo.pl/page/agreement/) prohibits
      data broadcast without a special agreement.
* IMGW (water levels in rivers)
    * IMGW has a [free API](https://danepubliczne.imgw.pl/apiinfo) for private use
* DX Info Centre (VHF Tropo propagation)
    * [DX Info Centre ToS](https://www.dxinfocentre.com/licence.htm) allow "Broadcast of text or verbal information
      derived from using the maps"
* RigReference (HF propagation data)
* RadioactiveAtHome - a BOINC project (radiation info)

## TODO

- Fix things that don't work :)
- Get rid of PHP dependency
- Package the project for easy installation
- Add local speech synthesis support
- Add local weather data sources (like HomeAssistant or [Nettigo Air Monitor](https://www.air.nettigo.pl/?lang=en))
- Work on internationalization

## Development

For development, clone this repository, install `dev.txt` requirements and run `pre-commit install`
to install pre-commit hooks.

## Hardware requirements

- An (old?) PC with a COM port (old thin clients anyone? :) )
- Amateur transceiver (for VHF band, ideally)
- PC-radio interface capable of driving radio's PTT

## OS requirements

* Linux
* Windows (if you manually install PHP, but PHP dependency removal is tracked in #6)

## Installation (for now)

NOTE: Packaging is tracked in #10

Required packages / Wymagane dodatkowe pakiety:

```
  sudo apt-get install git
  sudo apt-get install curl
  sudo apt-get install php7.0
  sudo apt-get install php7.0-curl
  sudo apt-get install php7.0-xml
  sudo apt-get install ffmpeg
```

* Clone this git repository
* Create a virtualenv for Python (`python -m venv venv`)
* Activate it
* Install `pip install -r requirements.txt`
* Configure `config.toml` to your liking
* Put the cron entry into crontab
  ```shell
    SHELL=/bin/bash
    */15 * * * * /path/to/virtualenv/bin/python /path/to/sr0wx.py > /dev/null
    ```

User rights for COM port / Uprawnienia usera do portu com

```

sudo gpasswd --add ${USER} dialout

```

## Audio sample re-generation

GENEROWANIE SAMPLI
Będąc w katalogu audio_generator:

```

cd audio_generator
php index.php

```

Only samples from `$slownik` array are generated. Other arrays are for storage.

Generowane są sample z tablicy `$słownik` z pliku slownik.php.
Pozostałe tablice to tylko przechowalnia fraz go wygenerowania.

## Credits

* Michał SQ6JNX - original creator
* Paweł SQ9ATK - maintainer of sq9atk/sr0wx and wx.ostol.pl
* responsivevoice.org - voice samples
