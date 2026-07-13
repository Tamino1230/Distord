#!/bin/bash

cd "../App/"

python -m PyInstaller --version
python -m PyInstaller --clean distord.spec

cd "dist"
cp -f "Distord" "../../Build/Distord-Linux"

chmod +x "../../Build/Distord-Linux"