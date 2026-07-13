#!/bin/bash

set -e

python -m PyInstaller --clean distord.spec

cp dist/Distord ./Distord-Linux
chmod +x ./Distord