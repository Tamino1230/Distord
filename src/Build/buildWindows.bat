
cd "../App/"

python -m PyInstaller --version
python -m PyInstaller --clean distord.spec

cd "dist"
copy /Y "Distord.exe" "../../Build/Distord.exe"