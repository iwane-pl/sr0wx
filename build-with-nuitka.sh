#!/bin/bash

python -m nuitka --follow-imports --include-plugin-directory=plugins --include-plugin-directory=speech sr0wx.py
