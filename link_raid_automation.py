import colorsys
import configparser
import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path

import keyboard
import numpy as np
import pyautogui
import pydirectinput
import pygetwindow
import pytesseract
from PIL import ImageGrab
from requests import get

pydirectinput.FAILSAFE = False

CONFIG_FILE = "link-raid-automation-settings.ini"

ini_config = configparser.ConfigParser()
defaults = {
    "default_team": "LR Auto",
    "join_diff": "4-8",
    "host_diff": "4",
    "auto_host": "true",
    "first_host_of_the_day_diff": "8",
    "debug_mode": "false",
    "document_daily_reward": "true",
    "refill_lp": "false",
    "exe_name": "MadokaExedra",
    "join_friends": "false",
    "join_community": "false",
    "only_join_friends_and_community": "false",
    "join_friends_and_community_max_difficulty": "",
}
join_team_override_defaults = {str(i): "" for i in range(1, 21)}

ini_config.read(CONFIG_FILE)
ini_config["general"] = {
    **defaults,
    **(ini_config["general"] if "general" in ini_config else {}),
}
ini_config["team_overrides"] = {
    **join_team_override_defaults,
    **(ini_config["team_overrides"] if "team_overrides" in ini_config else {}),
}

with open(CONFIG_FILE, "w", encoding="utf-8", newline="\n") as f:
    ini_config.write(f)

DEBUG = ini_config.getboolean("general", "debug_mode")
if DEBUG:
    os.makedirs("debug/logs", exist_ok=True)

default_team = ini_config.get("general", "default_team").replace(" ", "").lower()
JOIN_DIFF = ini_config.get("general", "join_diff")
if "-" in JOIN_DIFF:
    start, end = map(int, JOIN_DIFF.split("-"))
    LEVELS_TO_FIND = list(range(start, end + 1))
else:
    LEVELS_TO_FIND = [int(JOIN_DIFF)]

join_max_text: str = ini_config.get(
    "general", "join_friends_and_community_max_difficulty"
)
if join_max_text.isdigit():
    JOIN_MAX_DIFFICULTY = int(join_max_text)
else:
    JOIN_MAX_DIFFICULTY = LEVELS_TO_FIND[-1]

HOST_DIFF = ini_config.getint("general", "host_diff")
first_host_text: str = ini_config.get("general", "first_host_of_the_day_diff")
if first_host_text.isdigit():
    FIRST_HOST_DIFF = int(first_host_text)
else:
    FIRST_HOST_DIFF = HOST_DIFF

DO_HOST = ini_config.getboolean("general", "auto_host")
DO_REFILL = ini_config.getboolean("general", "refill_lp")

DAILY_SCREENSHOT = ini_config.getboolean("general", "document_daily_reward")
TARGET_WINDOW = ini_config.get("general", "exe_name")

JOIN_FRIENDS = ini_config.getboolean("general", "join_friends")
JOIN_COMMUNITY = ini_config.getboolean("general", "join_community")
ONLY_JOIN_FRIENDS_AND_COMMUNITY = ini_config.getboolean(
    "general", "only_join_friends_and_community"
)

teams = {
    **{i: default_team for i in range(1, 21)},
    **{
        i: ini_config.get("team_overrides", str(i)).replace(" ", "").lower()
        for i in range(1, 21)
        if ini_config.get("team_overrides", str(i)).strip()
    },
}

keyboard.add_hotkey("ctrl+shift+q", lambda: os._exit(0))

log_formatter = logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("lr_automation")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

if DEBUG:
    file_handler = logging.FileHandler(
        f"debug/logs/{datetime.today().strftime('%Y-%m-%dT%H-%M-%S')}.txt",
        encoding="utf-8",
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)


FRIEND_FILE = "friends.txt"
friend_file = Path(FRIEND_FILE)
friend_file.touch(exist_ok=True)
friends = [
    re.sub(r"[^A-Za-z0-9]", "", f.lower().replace(" ", ""))
    for f in friend_file.read_text(encoding="utf-8").split("\n")
]
friends = {f for f in friends if len(f) > 2}
resp = get(
    "https://raw.githubusercontent.com/thefrozenfishy/exedra-link-raid-automation/main/community.txt",
    timeout=3,
)
if resp.ok:
    community = [
        re.sub(r"[^A-Za-z0-9]", "", f.lower().replace(" ", ""))
        for f in resp.text.splitlines()
    ]
else:
    logging.error("Failed to fetch community members list.")
    community = []
community = {c for c in community if len(c) > 2}

tessaract_whitelist = "--psm 6 -c tessedit_char_whitelist={}"


def get_game_window():
    wins = pygetwindow.getWindowsWithTitle(TARGET_WINDOW)
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def _get_data_in_img(name: str, cords: tuple[int, int, int, int], config: str) -> dict:
    img = ImageGrab.grab(cords)
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT, config=config
    )

    if DEBUG:
        img.save(f"debug/{name}.png")
        logger.debug("%s > %s", name, data["text"])
    return data


def get_data_in_img_with_offset(
    x: int, y: int, offset: str, config: str, print_nr: int | None
):
    return _get_data_in_img(
        f"{offset}_{print_nr:03}" if print_nr else offset,
        (
            x + text_locations[offset][0],
            y + text_locations[offset][1],
            x + text_locations[offset][2],
            y + text_locations[offset][3],
        ),
        config,
    )


def get_data_in_img(cords: str, config: str):
    return _get_data_in_img(cords, text_locations[cords], config)


def get_text_in_img_with_offset(
    x: int, y: int, offset: str, config="", print_nr=None
) -> str:
    data = get_data_in_img_with_offset(x, y, offset, config=config, print_nr=print_nr)
    return re.sub(r"[^A-Za-z0-9]", "", "".join(data["text"]).lower().replace(" ", ""))


def get_nrs_in_img(cords: str) -> str:
    return (
        get_text_in_img(cords, config=tessaract_whitelist.format("0123456789ilI"))
        .replace("i", "1")
        .replace("I", "1")
        .replace("l", "1")
    )


def get_text_in_img(cords: str, config="") -> str:
    data = get_data_in_img(cords, config)
    return re.sub(r"[^A-Za-z0-9]", "", "".join(data["text"]).lower().replace(" ", ""))


def get_color_diff_range(x: int, y: int, offset: str) -> set[int]:
    colour_img = ImageGrab.grab(
        (
            x + text_locations[offset][0],
            y + text_locations[offset][1] + 20,
            x + text_locations[offset][0] + 2,
            y + text_locations[offset][1] + 22,
        )
    )
    arr = np.array(colour_img).astype(float) / 255.0
    avg_rgb = arr.mean(axis=(0, 1))  # [R, G, B] normalized
    r, g, b = avg_rgb

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360

    if DEBUG:
        colour_img.save(f"debug/colour_img_{h:.0f}_{s:.2f}_{v:.2f}.png")

    if 230 < h < 250 and s < 0.05 and v > 0.75:
        return set(range(17, 21))  # White
    if 30 < h < 70 and s < 0.15 and 0.65 > v > 0.35:
        return set(range(1, 5))  # Gray
    if (h < 20 or h > 340) and s > 0.3:
        return set(range(9, 13))  # Red
    if 80 < h < 160 and s > 0.15:
        return set(range(5, 9))  # Green
    if 230 < h < 320 and s > 0.15:
        return set(range(13, 17))  # Purple

    logger.error("HSV was H=%.0f, S=%.2f, V=%.2f", h, s, v)
    if DEBUG:
        raise ValueError()
    return {0}


def find_coords_for_eligable_difficulty():
    data = get_data_in_img("join_anchor_box", "")
    for i, text in enumerate(data["text"]):
        if not "player" in text.lower():
            continue
        x = text_locations["join_anchor_box"][0] + data["left"][i]
        y = text_locations["join_anchor_box"][1] + data["top"][i] + data["height"][i]
        eligable_nrs = get_color_diff_range(x, y, "join_lvl_offset")
        eligable_nrs_str = "".join(set("".join(map(str, eligable_nrs))))
        if 1 in eligable_nrs:
            eligable_nrs_str += "ilI"
        logger.debug("eligible NRs %s", eligable_nrs_str)
        lvl = (
            get_text_in_img_with_offset(
                x,
                y,
                "join_lvl_offset",
                config=tessaract_whitelist.format(eligable_nrs_str),
                print_nr=join_nr,
            )
            .replace("i", "1")
            .replace("I", "1")
            .replace("l", "1")
        )
        if not lvl.isdigit():
            continue
        lvl = int(lvl)
        if JOIN_MAX_DIFFICULTY < lvl:
            continue
        username = get_text_in_img_with_offset(
            x,
            y,
            "join_username_offset",
        )
        union = get_text_in_img_with_offset(
            x,
            y,
            "union_offset",
        )
        if JOIN_FRIENDS and username in friends or "on" in union:
            return x, y
        if JOIN_COMMUNITY and username in community:
            return x, y
        if ONLY_JOIN_FRIENDS_AND_COMMUNITY:
            continue
        if lvl in LEVELS_TO_FIND:
            return x, y
    return 0, 0


def select_correct_team(team_name):
    for _ in range(10):
        if team_name.lower() in get_text_in_img("team_name"):
            return
        click(*text_locations["next_team"])
        pyautogui.sleep(0.2)
    raise RuntimeError(f'Could not find team named "{team_name}"')


def start_play():
    difficulty = get_nrs_in_img("current_difficulty")
    if not difficulty.isdigit():
        difficulty = get_nrs_in_img("current_difficulty_single_digit")
    select_correct_team(teams[int(difficulty)])
    click(*text_locations["play_button"])
    for _ in range(10):
        pyautogui.sleep(0.2)
        click(*text_locations["play_button"])


def set_correct_host_difficulty():
    target_diff = (
        FIRST_HOST_DIFF
        if "3" in get_nrs_in_img("games_until_daily_bonus")
        else HOST_DIFF
    )
    difficulty = ""
    for _ in range(20):
        difficulty = get_nrs_in_img("host_difficulty")
        if not difficulty.isdigit():
            continue
        if int(difficulty) < target_diff:
            click(*text_locations["host_increment"])
        elif int(difficulty) > target_diff:
            click(*text_locations["host_decrement"])
    if not difficulty.isdigit() or int(difficulty) != target_diff:
        logging.error("Could not set correct host difficulty")
        raise ValueError("Could not set correct host difficulty")


join_nr = 1


def is_scroll_at_bottom():
    scroll_bar_img = ImageGrab.grab(
        (
            text_locations["scroll_bar"][0],
            text_locations["scroll_bar"][1],
            text_locations["scroll_bar"][2],
            text_locations["scroll_bar"][3],
        )
    )
    scroll_bar_img.save("debug/scroll_bar.png")
    arr = np.array(scroll_bar_img).astype(float) / 255.0
    avg_rgb = arr.mean(axis=(0, 1))  # [R, G, B] normalized
    r, g, b = avg_rgb

    _, _, v = colorsys.rgb_to_hsv(r, g, b)
    return v > 0.3


def claim_battles():
    scroll_is_at_bottom = False
    current_battles = get_nrs_in_img("joined_battles")
    if current_battles.isdigit() and int(current_battles) <= 3:
        scroll_is_at_bottom = True
    i = 60
    while not scroll_is_at_bottom and i > 0:
        i -= 1
        click(
            text_locations["join_anchor_box"][0], text_locations["join_anchor_box"][1]
        )
        if "end" in get_text_in_img("join_button_box"):
            click(*text_locations["join_button"])
            return

        pydirectinput.moveTo(
            text_locations["scroll_location"][0],
            text_locations["scroll_location"][1],
        )
        pyautogui.scroll(-1)

        scroll_is_at_bottom = is_scroll_at_bottom()

    click(*text_locations["join_battles_tab"])


def start_join():
    global join_nr

    current_battles = get_nrs_in_img("joined_battles")
    if current_battles.isdigit() and int(current_battles) == 10:
        click(*text_locations["joined_battles_tab"])
        return
    scroll_is_at_bottom = False
    i = 60
    while not scroll_is_at_bottom and i > 0:
        i -= 1
        x, y = find_coords_for_eligable_difficulty()
        if x and y:
            click(x, y)
            pyautogui.sleep(0.5)

            click(*text_locations["join_button"])

            join_nr += 1
            return

        pydirectinput.moveTo(
            text_locations["scroll_location"][0],
            text_locations["scroll_location"][1],
        )
        pyautogui.scroll(-1)

        scroll_is_at_bottom = is_scroll_at_bottom()

    click(*text_locations["refresh_button"])


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    JOINED_BATTLES_SCREEN = "JOINED_BATTLES_SCREEN"
    HOST_SCREEN = "HOST_SCREEN"
    HOME_SCREEN_CAN_HOST = "HOME_SCREEN_CAN_HOST"
    HOME_SCREEN_CANNOT_HOST = "HOME_SCREEN_CANNOT_HOST"
    NO_ACTION = "NO_ACTION"
    RESULTS_SCREEN = "RESULTS_SCREEN"
    JOIN_BACK_SCREEN = "JOIN_BACK_SCREEN"
    HOST_BACK_SCREEN = "HOST_BACK_SCREEN"
    PLAY_JOIN_SCREEN = "PLAY_JOIN_SCREEN"
    PLAY_HOST_SCREEN = "PLAY_HOST_SCREEN"
    REFILL_LP = "REFILL_LP"
    DAILY_BONUS_COUNTER = "DAILY_BONUS_COUNTER"
    DAILY_BONUS = "DAILY_BONUS"
    BATTLE_ALREADY_ENDED = "BATTLE_ALREADY_ENDED"
    CONTINUE = "CONTINUE"


def current_state() -> CurrentState:
    text = get_text_in_img("result_box")
    if "lvl" in text.lower().replace("i", "l"):
        return CurrentState.RESULTS_SCREEN

    text = get_text_in_img("battle_already_ended")
    if "battlehas" in text.lower():
        return CurrentState.BATTLE_ALREADY_ENDED

    text = get_text_in_img("join_button_box")
    if "joln" in text.lower().replace("i", "l"):
        return CurrentState.JOIN_SCREEN
    if "etreat" in text.lower() or "ended" in text.lower():
        return CurrentState.JOINED_BATTLES_SCREEN

    text = get_text_in_img("daily_bonus_box").lower().replace("i", "l")
    if "dally" in text:
        if "rlng" in text:
            return CurrentState.REFILL_LP
        return CurrentState.DAILY_BONUS_COUNTER

    text = get_text_in_img("host_diff_box")
    if "lvl" in text.lower().replace("i", "l"):
        return CurrentState.HOST_SCREEN

    text = get_text_in_img("join_back_box")
    if "back" in text.lower():
        return CurrentState.JOIN_BACK_SCREEN

    text = get_text_in_img("host_back_box")
    if "back" in text.lower():
        return CurrentState.HOST_BACK_SCREEN

    text = get_text_in_img("party_box")
    if "party" in text.lower():
        text2 = get_text_in_img("play_box")
        if "play" in text2.lower():
            return CurrentState.PLAY_JOIN_SCREEN
        return CurrentState.PLAY_HOST_SCREEN

    text = get_text_in_img("can_host_box")
    if "play" in text.lower():
        if not DO_HOST:
            return CurrentState.HOME_SCREEN_CANNOT_HOST

        text2 = get_text_in_img("in_progress_box")
        if "vlewresults" in text2.lower().replace("i", "l"):
            return CurrentState.HOME_SCREEN_CAN_HOST

        text3 = get_text_in_img("in_progress_box")
        if "progress" not in text3.lower() and not all(
            str(i) not in text.removesuffix("6") for i in range(1, 7)
        ):
            return CurrentState.HOME_SCREEN_CAN_HOST
        return CurrentState.HOME_SCREEN_CANNOT_HOST

    text = get_text_in_img("daily_reward_box")
    if "ob" in text.lower().replace("i", "l"):
        return CurrentState.DAILY_BONUS

    text = get_text_in_img("tap_to_continue")
    if "contlnue" in text.lower().replace("i", "l"):
        return CurrentState.CONTINUE

    return CurrentState.NO_ACTION


text_locations = {}


def click(x: float | int, y: float | int):
    pydirectinput.click(int(x), int(y))
    pyautogui.moveTo(10, 10)


def setup_text_locations():
    win = get_game_window()
    try:
        win.activate()
    except Exception as e:
        logger.exception(
            """Could not activate window!
This is not a major issue, just be sure that no application is hiding Exedra from view. 
The OCR has to 'see' the content of the game to determine what to do.""",
            exc_info=e,
        )
    text_locations["result_box"] = (
        win.left + 0.23 * win.width,
        win.top + 0.785 * win.height,
        win.right - 0.725 * win.width,
        win.bottom - 0.172 * win.height,
    )
    text_locations["scroll_bar"] = (
        win.left + 0.68 * win.width,
        win.top + 0.85 * win.height,
        win.right - 0.31 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["daily_bonus_box"] = (
        win.left + 0.3 * win.width,
        win.top + 0.1 * win.height,
        win.right - 0.3 * win.width,
        win.bottom - 0.7 * win.height,
    )
    text_locations["daily_reward_box"] = (
        win.left + 0.4 * win.width,
        win.top + 0.28 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.62 * win.height,
    )
    text_locations["daily_reward_pic_box"] = (
        win.left + 0.35 * win.width,
        win.top + 0.35 * win.height,
        win.right - 0.35 * win.width,
        win.bottom - 0.4 * win.height,
    )
    text_locations["join_back_box"] = (
        win.left + 0.45 * win.width,
        win.top + 0.81 * win.height,
        win.right - 0.45 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["host_back_box"] = (
        win.left + 0.55 * win.width,
        win.top + 0.81 * win.height,
        win.right - 0.35 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["team_name"] = (
        win.left + 0.4 * win.width,
        win.top + 0.44 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["party_box"] = (
        win.left + 0.29 * win.width,
        win.top + 0.44 * win.height,
        win.right - 0.65 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["play_box"] = (
        win.left + 0.5 * win.width,
        win.top + 0.79 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.15 * win.height,
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["join_button_box"] = (
        win.left + 0.8 * win.width,
        win.top + 0.8 * win.height,
        win.right - 0.1 * win.width,
        win.bottom - 0.14 * win.height,
    )
    text_locations["battle_already_ended"] = (
        win.left + 0.4 * win.width,
        win.top + 0.45 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.45 * win.height,
    )
    text_locations["games_until_daily_bonus"] = (
        win.left + 0.64 * win.width,
        win.top + 0.74 * win.height,
        win.right - 0.34 * win.width,
        win.bottom - 0.21 * win.height,
    )
    text_locations["battle_already_ended_ok"] = (
        int(win.left + 0.5 * win.width),
        int(win.top + 0.75 * win.height),
    )
    text_locations["joined_battles"] = (
        win.left + 0.54 * win.width,
        win.top + 0.05 * win.height,
        win.right - 0.43 * win.width,
        win.bottom - 0.85 * win.height,
    )
    text_locations["join_battles_tab"] = (
        int(win.left + 0.2 * win.width),
        int(win.top + 0.2 * win.height),
    )
    text_locations["joined_battles_tab"] = (
        int(win.left + 0.2 * win.width),
        int(win.top + 0.3 * win.height),
    )
    text_locations["play_button"] = (
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["refresh_button"] = (
        int(win.left + 0.31 * win.width),
        int(win.top + 0.09 * win.height),
    )
    text_locations["join_screen_button"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.82 * win.height),
    )
    text_locations["host_screen_button"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["next_team"] = (
        int(win.left + 0.28 * win.width),
        int(win.top + 0.58 * win.height),
    )
    text_locations["scroll_location"] = (
        win.left + 2 * win.width // 3,
        win.top + win.height // 2,
    )
    text_locations["like_box"] = (
        win.left + 0.12 * win.width,
        win.top + 0.18 * win.height,
        win.right - 0.83 * win.width,
        win.bottom - 0.77 * win.height,
    )
    text_locations["join_anchor_box"] = (
        win.left + 0.43 * win.width,
        win.top + 0.29 * win.height,
        win.right - 0.51 * win.width,
        win.bottom - 0.6 * win.height,
    )
    text_locations["join_lvl_offset"] = (
        0.072 * win.width,
        -0.13 * win.height,
        0.095 * win.width,
        -0.08 * win.height,
    )
    text_locations["join_username_offset"] = (
        -0.19 * win.width,
        -0.02 * win.height,
        -0.01 * win.width,
        0.005 * win.height,
    )
    text_locations["union_offset"] = (
        -0.05 * win.width,
        -0.16 * win.height,
        -0.01 * win.width,
        -0.13 * win.height,
    )
    text_locations["host_diff_box"] = (
        win.left + 0.68 * win.width,
        win.top + 0.17 * win.height,
        win.right - 0.22 * win.width,
        win.bottom - 0.79 * win.height,
    )
    text_locations["host_button"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["can_host_box"] = (
        win.left + 0.32 * win.width,
        win.top + 0.82 * win.height,
        win.right - 0.57 * win.width,
        win.bottom - 0.13 * win.height,
    )
    text_locations["in_progress_box"] = (
        win.left + 0.3 * win.width,
        win.top + 0.75 * win.height,
        win.right - 0.55 * win.width,
        win.bottom - 0.15 * win.height,
    )
    text_locations["tap_to_continue"] = (
        win.left + 0.4 * win.width,
        win.top + 0.85 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.05 * win.height,
    )
    text_locations["host_difficulty"] = (
        win.left + 0.73 * win.width,
        win.top + 0.17 * win.height,
        win.right - 0.22 * win.width,
        win.bottom - 0.78 * win.height,
    )
    text_locations["host_decrement"] = (
        int(win.left + 0.64 * win.width),
        int(win.top + 0.19 * win.height),
    )
    text_locations["host_increment"] = (
        int(win.left + 0.84 * win.width),
        int(win.top + 0.19 * win.height),
    )
    text_locations["current_difficulty"] = (
        win.left + 0.44 * win.width,
        win.top + 0.08 * win.height,
        win.right - 0.52 * win.width,
        win.bottom - 0.87 * win.height,
    )
    text_locations["current_difficulty_single_digit"] = (
        text_locations["current_difficulty"][0] + 3,
        text_locations["current_difficulty"][1],
        text_locations["current_difficulty"][2] - 3,
        text_locations["current_difficulty"][3],
    )
    text_locations["resolution"] = (win.width, win.height)


def main():
    setup_text_locations()
    logger.info("starting with config: %s", dict(ini_config["general"]))
    logger.info(
        "Considering %d friends and %d community members", len(friends), len(community)
    )
    logger.info("Press Ctrl+Shift+Q to terminate the program.")
    while True:
        pyautogui.sleep(1)
        state = current_state()
        logger.info("Current State: %s", state.name)
        match state:
            case CurrentState.JOINED_BATTLES_SCREEN:
                claim_battles()
            case CurrentState.JOIN_SCREEN:
                start_join()
            case CurrentState.REFILL_LP:
                if DO_REFILL:
                    click(
                        int(text_locations["host_back_box"][0]),
                        int(text_locations["host_back_box"][1]),
                    )
                else:
                    logger.info("Out of LP")
                    return
            case CurrentState.HOST_SCREEN:
                set_correct_host_difficulty()
                click(*text_locations["host_button"])
            case CurrentState.HOME_SCREEN_CAN_HOST:
                click(*text_locations["host_screen_button"])
            case CurrentState.BATTLE_ALREADY_ENDED:
                click(*text_locations["battle_already_ended_ok"])
            case CurrentState.HOME_SCREEN_CANNOT_HOST:
                click(*text_locations["join_screen_button"])
            case CurrentState.PLAY_JOIN_SCREEN:
                logger.info("Joining a game...")
                start_play()
            case CurrentState.PLAY_HOST_SCREEN:
                logger.info("Hosting a game...")
                start_play()
            case CurrentState.NO_ACTION:
                pyautogui.sleep(5)
            case CurrentState.RESULTS_SCREEN:
                click(
                    int(text_locations["result_box"][2]),
                    int(text_locations["result_box"][3]),
                )
            case CurrentState.JOIN_BACK_SCREEN:
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
                pyautogui.sleep(2)
            case CurrentState.HOST_BACK_SCREEN:
                click(
                    int(text_locations["host_back_box"][0]),
                    int(text_locations["host_back_box"][1]),
                )
                pyautogui.sleep(2)
            case CurrentState.CONTINUE:
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
            case CurrentState.DAILY_BONUS_COUNTER:
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
            case CurrentState.DAILY_BONUS:
                if DAILY_SCREENSHOT:
                    img = ImageGrab.grab(text_locations["daily_reward_pic_box"])
                    os.makedirs("daily_reward", exist_ok=True)
                    img.save(
                        f"daily_reward/{datetime.today().strftime('%Y-%m-%dT%H-%M-%S')}.png"
                    )

                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )


if __name__ == "__main__":
    main()
