# Link raid automation tool for Exedra

## Requires

* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and added to PATH.

## Usage

* This assumes your game runs in 16:9 aspect ratio. I have not tested on emulator myself so do tell if it doesn't work
* Download exe from releases and run. Keep in mind the window needs to be visible for the OCR to function properly, similar to the crys farm tool.
* The file will run infinitely, hosting whenever able, otherwise joining the first battle it finds in your desired range.
* Configure settings in `link-raid-automation-settings.ini`. This file is created automatically on first run with default settings.
  * ``default_team`` Team name to use when doing Link Raid.
    * Note: this _must_ match a team name you have. Do note that numbers and only small letters are more likely to be read wrong, prefer using capitalized words without numbers for the best experience.
  * ``join_diff`` for multiple difficulties to be chosen by writing e.g. "9-12" meaning 9 to 12 inclusive.  
  * ``auto_host`` Set this to true if you wish the game to automatically host games, false for the application to only join games.
  * ``host_diff`` Which difficulty you wish the game to host battles in.
  * ``first_host_of_the_day_diff`` If set the first host battle of the day will use this difficulty instead of ``host_diff``.
  * ``debug_mode`` Enable to save OCR screen grabs to a debug folder and log detailed.
  * ``refill_lp`` Use 3 rings to refill LP daily.
  * ``document_daily_reward`` Take screenshot of the daily reward.
  * ``exe_name`` is the name of the exe as shown in task manager. Change if you renamed the exe or are using an emulator.
  * ``join_friends`` Enable this to always join games where any of the top 3 players in a raid are in your local friends.txt file or your union, given that the difficulty is below ``join_friends_and_community_max_difficulty``.
    * Top 3 players shows are sorted alphabetically
  * ``join_community`` Enable this to always join games where any of the top 3 players in a raid are in the [community file](https://github.com/thefrozenfishy/exedra-link-raid-automation/blob/main/community.txt), given that the difficulty is below ``join_friends_and_community_max_difficulty``.
    * Add yourself to the [community list](https://thefrozenfishy.github.io/exedra-dmg-calc/#/link-raid) using this form.
  * ``only_join_friends_and_community`` Ignore all games that are not friends or community.
  * ``join_friends_and_community_max_difficulty`` The max difficulty to join friends and community stages in. Defaults to the highest difficulty given in ``join_diff``.
  * ``team_overrides`` If you for some difficulties wish to run other teams than ``default_team`` you can override it here.
  * ``love_everyone`` ♥ everyone in your matches

### Crystalis farming

The tool is able to swap between crys farming and link raids once running out of QP or LP, allowing for the tool to completely farm both modes to depletion.

* ``swap_to_crys_farm_after_link_raid`` If you want the tool to swap to link raid once crys farming is done.
* ``swap_to_link_raid_after_crys_farm`` If you want the tool to swap to crys farming once link raid is done.
* ``team`` What team should be used in crys farm.
  * Note: this _must_ match a team name you have. Do note that numbers and only small letters are more likely to be read wrong, prefer using capitalized words without numbers for the best experience.
* ``element`` What element stage should be run in crys farm.
  * The valid elements are: ``flame``, ``aqua``, ``forest``, ``light``, ``dark`` and ``void``.
* ``refill_qp`` Use 8 cubes to refill QP daily.
* ``document_ex_drops`` Take screenshot of all dropped ex Crystalises.

## Bug notes

* The OCR is a bit touchy, so some actions like scrolling manually in the join list or various resolutions can mess things up. just changing screens will resolve any issue. I run Windowed 1024x576, so that's the best tested resolution.
