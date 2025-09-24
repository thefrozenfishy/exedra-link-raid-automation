# Link raid automation tool for Exedra

## Requires

* Tesseract OCR installed and added to PATH. <https://github.com/tesseract-ocr/tesseract/releases>

## Usage

* Download exe from releases and run.
* Configure settings in `link-raid-automation-settings.ini` file (Will be created on first run with default settings).
  * ``join_diff`` for multiple difficulties to be chosen by writing e.g. "9-12" meaning 9 to 12 inclusive.
  * ``exe_name`` is the name of the exe as shown in task manager. Change if you renamed the exe or are using an emulator.

## TODOs

* Auto claim finished raids
* Do host first then join later without manual inputs
* Add thing to use rings for more later
* Handle daily rewards
* Avoid dead runs
* Avoid deserted runs
* Avoid runs w less then X minutes remaining
