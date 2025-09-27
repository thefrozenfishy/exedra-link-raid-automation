# Link raid automation tool for Exedra

## Requires

* Tesseract OCR installed and added to PATH. <https://github.com/tesseract-ocr/tesseract/releases>

## Usage

* This assumes your game runs in 16:9 aspect ratio. I have not tested on emulator myself so do tell if it doesn't work
* Download exe from releases and run. Keep in mind the window needs to be visible for the OCR to function properly, similar to the crys farm tool.
* The file will run infinitely, hosting whenever able, otherwise joining the first battle it finds in your desired range.
* Configure settings in `link-raid-automation-settings.ini`. This file is created automatically on first run with default settings.
  * ``default_team`` Team name to use when doing Link Raid.
  * ``join_diff`` for multiple difficulties to be chosen by writing e.g. "9-12" meaning 9 to 12 inclusive.  
  * ``auto_host`` Set this to true if you wish the game to automatically host games, false for the application to only join games.
  * ``host_diff`` Which difficulty you wish the game to host battles in.
  * ``first_host_of_the_day_diff`` If set the first host battle of the day will use this difficulty instead of ``host_diff``.
  * ``debug_mode`` Enable to save OCR screen grabs to a debug folder and log detailed.
  * ``document_daily_reward`` Take screenshot of the daily reward.
  * ``exe_name`` is the name of the exe as shown in task manager. Change if you renamed the exe or are using an emulator.
  * ``join_friends`` Enable this to always join games where the hostname is in your local friends.txt file or your union, given that the difficulty is below ``join_friends_and_community_max_difficulty``.
  * ``join_community`` Enable this to always join games where the hostname is in the [community file](https://github.com/thefrozenfishy/exedra-link-raid-automation/blob/main/community.txt), given that the difficulty is below ``join_friends_and_community_max_difficulty``.
    * Add yourself to the [community list](https://thefrozenfishy.github.io/exedra-dmg-calc/#/link-raid) using this form.
  * ``only_join_friends_and_community`` Ignore all games that are not friends or community.
  * ``join_friends_and_community_max_difficulty`` The max difficulty to join friends and community stages in. Defaults to the highest difficulty given in ``join_diff``.
  * ``team_overrides`` If you for some difficulties wish to run other teams than ``default_team`` you can override it here.

## TODOs

* Add option to use rings for more LR
* Love everyone mode! (Heart everyone if true, default true <3)
* Actually implement first host of the day code
