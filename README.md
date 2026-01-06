Need this req:

# python3:
winget install -e --id Python.Python.3

#Req lib:
pip install pandas undetected-chromedriver beautifulsoup4 selenium


# Eventually a bat file:

@echo off
cd /d "%~dp0"
python3 "Immobiliare_webscraping.py"
pause
