# Link raid automation tool for Exedra

## Requires

* Tesseract OCR installed and added to PATH. <https://github.com/tesseract-ocr/tesseract/releases>

## Usage

* This assumes your game runs in 16:9 aspect ratio. I have not tested on emulator myself so do tell if it doesn't work
* Download exe from releases and run.
* Configure settings in `link-raid-automation-settings.ini` file (Will be created on first run with default settings).
  * ``host_team`` Team name which should be used when hosting.
  * ``join_team`` Team name to use when joining.
  * ``join_diff`` for multiple difficulties to be chosen by writing e.g. "9-12" meaning 9 to 12 inclusive.  
  * ``debug_mode`` Enable to save OCR screen grabs to a debug folder and log detailed.
  * ``document_daily_reward`` Take screenshot of the daily reward
  * ``exe_name`` is the name of the exe as shown in task manager. Change if you renamed the exe or are using an emulator.
  * ``max_scroll_attempts`` How many times the program should scroll down before refreshing the join list.

## TODOs

* Auto claim finished raids
* Add option to use rings for more LR
* Avoid dead runs
* Avoid deserted runs
* Avoid runs w less then X minutes remaining
