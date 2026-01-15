# Need this req:

winget install -e --id Python.Python.3

pip install --upgrade setuptools pandas undetected-chromedriver beautifulsoup4 selenium openpyxl

# Eventually a bat file:
@echo off

cd /d "%~dp0"

python3 "Immobiliare_webscraping.py"

pause
