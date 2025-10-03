import colorsys
import configparser
import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from random import random

import cv2
import keyboard
import numpy as np
import pyautogui
import pydirectinput
import pygetwindow
import pytesseract
from PIL import Image, ImageDraw, ImageGrab
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

crys_defaults = {
    "swap_to_crys_farm_after_link_raid": "true",
    "swap_to_link_raid_after_crys_farm": "true",
    "document_ex_drops": "true",
    "team": "Crys Farm",
    "element": "aqua",
    "refill_qp": "false",
}

ini_config.read(CONFIG_FILE)
ini_config["general"] = {
    **defaults,
    **(ini_config["general"] if "general" in ini_config else {}),
}
ini_config["team_overrides"] = {
    **join_team_override_defaults,
    **(ini_config["team_overrides"] if "team_overrides" in ini_config else {}),
}
ini_config["crystalis"] = {
    **crys_defaults,
    **(ini_config["crystalis"] if "crystalis" in ini_config else {}),
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
DO_REFILL_LP = ini_config.getboolean("general", "refill_lp")
LR_TO_CRYS_SWAP = ini_config.getboolean(
    "crystalis", "swap_to_crys_farm_after_link_raid"
)
CRYS_TO_LR_SWAP = ini_config.getboolean(
    "crystalis", "swap_to_link_raid_after_crys_farm"
)
CRYS_TEAM = ini_config.get("crystalis", "team").replace(" ", "").lower()
CRYS_ELEMENT = ini_config.get("crystalis", "element").lower().strip()
valid_elements = ("flame", "aqua", "forest", "light", "dark", "void")
if CRYS_ELEMENT not in valid_elements:
    input(f"ERROR: element must be one of {', '.join(valid_elements)}")
DO_REFILL_QP = ini_config.getboolean("crystalis", "refill_qp")
CRYS_EX_SCREENSHOT = ini_config.getboolean("crystalis", "document_ex_drops")

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


def normalize_1(s: str) -> str:
    return (
        s.replace("i", "1")
        .replace("I", "1")
        .replace("l", "1")
        .replace("]", "1")
        .replace("[", "1")
    )


def get_text_in_img(cords: str, config="", print_nr=None, make_bw=False) -> str:
    img = ImageGrab.grab(text_locations[cords])
    if make_bw:
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        _, img_data = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        img_data = img
    try:
        data = pytesseract.image_to_data(
            img_data, output_type=pytesseract.Output.DICT, config=config
        )
    except pytesseract.TesseractNotFoundError as e:
        input(
            "Tesseract is not in path! Download it and restart your pc and try again..."
        )
        raise e
    if DEBUG:
        name = f"{cords}_{print_nr:03}" if print_nr else cords
        img.save(f"debug/{name}.png")
        if make_bw:
            Image.fromarray(img_data).save(f"debug/{name}_bw.png")
        logger.debug("%s > %s", name, data["text"])
    return re.sub(r"[^A-Za-z0-9]", "", "".join(data["text"]).lower().replace(" ", ""))


def get_nrs_in_img(cords: str) -> str:
    return normalize_1(
        get_text_in_img(cords, config=tessaract_whitelist.format("0123456789ilI"))
    )


def get_color_diff_range(offset: str) -> set[int]:
    colour_img = ImageGrab.grab(
        (
            text_locations[offset][0] + 5,
            text_locations[offset][1] + 10,
            text_locations[offset][0] + 10,
            text_locations[offset][1] + 15,
        )
    )
    arr = np.array(colour_img).astype(float) / 255.0
    avg_rgb = arr.mean(axis=(0, 1))  # [R, G, B] normalized
    r, g, b = avg_rgb

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360

    if DEBUG:
        colour_img.save(f"debug/colour_img_{h:.0f}_{s:.2f}_{v:.2f}.png")

    if 230 < h < 250 and s < 0.05:
        return set(range(17, 21))  # White
    if (30 < h < 70 and s < 0.15 and 0.65 > v > 0.35) or (
        h < 30 and s < 0.1 and v < 0.3
    ):
        # Different colour in host and join screens for some reason
        return set(range(1, 5))  # Gray
    if (h < 20 or h > 340) and s > 0.3:
        return set(range(9, 13))  # Red
    if 80 < h < 160 and s > 0.15:
        return set(range(5, 9))  # Green
    if 230 < h < 320 and s > 0.15:
        return set(range(13, 17))  # Purple

    logger.error("HSV was H=%.0f, S=%.2f, V=%.2f", h, s, v)
    return {0}


def find_coords_for_eligable_difficulty() -> bool:
    eligable_nrs = get_color_diff_range("join_lvl")
    eligable_nrs_str = "".join(set("".join(map(str, eligable_nrs))))
    if 1 in eligable_nrs:
        eligable_nrs_str += "ilI"
    logger.debug("eligible NRs %s", eligable_nrs_str)
    lvl = normalize_1(
        get_text_in_img(
            "join_lvl",
            config=tessaract_whitelist.format("Lvl" + eligable_nrs_str),
            print_nr=join_nr,
        )
    )
    lvl = lvl.removeprefix("1v1").removeprefix(".")
    if not lvl.isdigit():
        return False
    lvl = int(lvl)
    if lvl not in eligable_nrs and lvl + 10 in eligable_nrs:
        lvl += 10
    if lvl not in eligable_nrs and lvl - 10 in eligable_nrs:
        lvl -= 10
    logger.debug("Found lvl %d", lvl)
    if JOIN_MAX_DIFFICULTY < lvl:
        return False
    for i in range(3):
        username = get_text_in_img(f"join_username_{i}")
        union = get_text_in_img(f"union_{i}")
        logger.debug(
            "User%d was found to be '%s' with '%s' union flag", i, username, union
        )

        if not username.strip() and not union.strip():
            break
        if JOIN_FRIENDS and (username in friends or "on" in union.lower()):
            return True
        if JOIN_COMMUNITY and username in community:
            return True
    if ONLY_JOIN_FRIENDS_AND_COMMUNITY:
        return False
    if lvl in LEVELS_TO_FIND:
        return True
    return False


def select_correct_team(team_name, is_crys):
    for _ in range(15):
        if team_name.lower() in get_text_in_img(
            "crys_team_name" if is_crys else "team_name"
        ):
            return
        click(*text_locations["crys_next_team" if is_crys else "next_team"])
        pyautogui.sleep(0.2)
    raise RuntimeError(f'Could not find team named "{team_name}"')


def start_play():
    difficulty = get_nrs_in_img("current_difficulty")
    if not difficulty.isdigit():
        difficulty = get_nrs_in_img("current_difficulty_single_digit")
    select_correct_team(
        teams.get(int(difficulty) if difficulty.isdigit() else 0, default_team),
        is_crys=False,
    )
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
    lvl = ""
    for _ in range(60):
        eligable_nrs = get_color_diff_range("host_difficulty")
        eligable_nrs_str = "".join(set("".join(map(str, eligable_nrs))))
        if 1 in eligable_nrs:
            eligable_nrs_str += "ilI]["
        logger.debug("eligible host NRs %s", eligable_nrs_str)
        lvl = normalize_1(
            get_text_in_img(
                "host_difficulty",
                config=tessaract_whitelist.format(eligable_nrs_str),
                print_nr=join_nr,
            )
        )
        if not lvl.isdigit():
            click(
                *(
                    text_locations[
                        "host_decrement" if random() > 0.5 else "host_increment"
                    ]
                )
            )
            continue
        lvl = int(lvl)
        if lvl not in eligable_nrs and lvl + 10 in eligable_nrs:
            lvl += 10
        if lvl not in eligable_nrs and lvl - 10 in eligable_nrs:
            lvl -= 10
        if lvl < target_diff:
            click(*text_locations["host_increment"])
        elif lvl > target_diff:
            click(*text_locations["host_decrement"])
        else:
            break
    if not lvl:
        lvl = 0
    if int(lvl) != target_diff:
        logging.error(
            "Could not set correct host difficulty, found %d but wanted %d",
            lvl,
            target_diff,
        )
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
    if DEBUG:
        scroll_bar_img.save("debug/scroll_bar.png")
    arr = np.array(scroll_bar_img).astype(float) / 255.0
    avg_rgb = arr.mean(axis=(0, 1))  # [R, G, B] normalized
    r, g, b = avg_rgb

    _, _, v = colorsys.rgb_to_hsv(r, g, b)
    logger.debug("Scroll bar has v=%.2f", v)
    return v > 0.3


def claim_battles():
    scroll_is_at_bottom = False
    current_battles = get_nrs_in_img("joined_battles")
    if current_battles.isdigit() and int(current_battles) <= 3:
        scroll_is_at_bottom = True
    i = 60
    while not scroll_is_at_bottom and i > 0:
        i -= 1
        if "end" in get_text_in_img("join_button_box"):
            click(*text_locations["join_button"])
            return

        pydirectinput.click(*text_locations["scroll_location"])
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
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
        valid_match = find_coords_for_eligable_difficulty()
        if valid_match:
            click(*text_locations["join_button"])
            pyautogui.sleep(2)
            join_nr += 1
            return

        pydirectinput.click(*text_locations["scroll_location"])
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
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
    CRYS_RESULTS_SCREEN = "CRYS_RESULTS_SCREEN"
    CRYS_RETRY_SCREEN = "CRYS_RETRY_SCREEN"
    JOIN_BACK_SCREEN = "JOIN_BACK_SCREEN"
    HOST_BACK_SCREEN = "HOST_BACK_SCREEN"
    PLAY_JOIN_SCREEN = "PLAY_JOIN_SCREEN"
    PLAY_HOST_SCREEN = "PLAY_HOST_SCREEN"
    REFILL_LP = "REFILL_LP"
    REFILL_QP = "REFILL_QP"
    DAILY_BONUS_COUNTER = "DAILY_BONUS_COUNTER"
    DAILY_BONUS = "DAILY_BONUS"
    BATTLE_ALREADY_ENDED = "BATTLE_ALREADY_ENDED"
    EX_SCREEN = "EX_SCREEN"
    CONTINUE = "CONTINUE"


def current_state() -> CurrentState:
    if "1v1" in normalize_1(get_text_in_img("result_box")):
        return CurrentState.RESULTS_SCREEN

    if "retry" in normalize_1(get_text_in_img("crys_retry_box")):
        return CurrentState.CRYS_RETRY_SCREEN

    if "bta1ned" in normalize_1(
        get_text_in_img("crys_result_box")
    ) or "esu1t" in normalize_1(get_text_in_img("crys_result_box2")):
        return CurrentState.CRYS_RESULTS_SCREEN

    if "batt1ehas" in normalize_1(get_text_in_img("battle_already_ended")):
        return CurrentState.BATTLE_ALREADY_ENDED

    text = normalize_1(get_text_in_img("join_button_box"))
    if "jo1n" in text:
        return CurrentState.JOIN_SCREEN
    if "etreat" in text or "ended" in text:
        return CurrentState.JOINED_BATTLES_SCREEN

    text = normalize_1(get_text_in_img("daily_bonus_box"))
    if "da11y" in text:
        if "r1ng" in text:
            return CurrentState.REFILL_LP
        if "cube" in text:
            return CurrentState.REFILL_QP
        return CurrentState.DAILY_BONUS_COUNTER

    if "round" in get_text_in_img("round_box"):
        return CurrentState.HOST_SCREEN

    if "back" in get_text_in_img("join_back_box"):
        return CurrentState.JOIN_BACK_SCREEN

    if "back" in get_text_in_img("host_back_box"):
        return CurrentState.HOST_BACK_SCREEN

    text = normalize_1(get_text_in_img("party_box"))
    if "party" in text:
        text2 = get_text_in_img("play_box")
        if "p1ay" in text2.lower():
            return CurrentState.PLAY_JOIN_SCREEN
        return CurrentState.PLAY_HOST_SCREEN

    if "v1ewresu1ts" in normalize_1(get_text_in_img("in_progress_box")):
        return CurrentState.HOME_SCREEN_CAN_HOST

    text = normalize_1(get_text_in_img("can_host_box"))
    if "p1ay" in text:
        if not DO_HOST:
            return CurrentState.HOME_SCREEN_CANNOT_HOST

        progress_text = get_text_in_img("in_progress_box")
        if "progress" not in progress_text.lower() and "06" not in text:
            return CurrentState.HOME_SCREEN_CAN_HOST
        return CurrentState.HOME_SCREEN_CANNOT_HOST

    if "ob" in get_text_in_img("daily_reward_box", make_bw=True):
        return CurrentState.DAILY_BONUS

    if "cont1nue" in normalize_1(get_text_in_img("tap_to_continue")):
        return CurrentState.CONTINUE

    if "cont" in normalize_1(get_text_in_img("ex_continue_box")):
        return CurrentState.EX_SCREEN

    return CurrentState.NO_ACTION


text_locations = {}


def click(x: float | int, y: float | int):
    curr = pyautogui.position()
    pydirectinput.click(int(x), int(y))
    pyautogui.moveTo(curr)


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
        int(win.left + 0.23 * win.width),
        int(win.top + 0.785 * win.height),
        int(win.right - 0.725 * win.width),
        int(win.bottom - 0.172 * win.height),
    )
    text_locations["scroll_bar"] = (
        int(win.left + 0.68 * win.width),
        int(win.top + 0.85 * win.height),
        int(win.right - 0.31 * win.width),
        int(win.bottom - 0.12 * win.height),
    )
    text_locations["ex_continue_box"] = (
        int(win.left + 0.75 * win.width),
        int(win.top + 0.85 * win.height),
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.1 * win.height),
    )
    text_locations["daily_bonus_box"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.1 * win.height),
        int(win.right - 0.3 * win.width),
        int(win.bottom - 0.7 * win.height),
    )
    text_locations["lp_refills_remaining"] = (
        int(win.left + 0.5 * win.width),
        int(win.top + 0.55 * win.height),
        int(win.right - 0.45 * win.width),
        int(win.bottom - 0.4 * win.height),
    )
    text_locations["qp_refills_remaining"] = (
        int(win.left + 0.5 * win.width),
        int(win.top + 0.55 * win.height),
        int(win.right - 0.45 * win.width),
        int(win.bottom - 0.35 * win.height),
    )
    text_locations["daily_reward_box"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.28 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.62 * win.height),
    )
    text_locations["daily_reward_pic_box"] = (
        int(win.left + 0.35 * win.width),
        int(win.top + 0.35 * win.height),
        int(win.right - 0.35 * win.width),
        int(win.bottom - 0.4 * win.height),
    )
    text_locations["join_back_box"] = (
        int(win.left + 0.45 * win.width),
        int(win.top + 0.81 * win.height),
        int(win.right - 0.45 * win.width),
        int(win.bottom - 0.12 * win.height),
    )
    text_locations["host_back_box"] = (
        int(win.left + 0.55 * win.width),
        int(win.top + 0.81 * win.height),
        int(win.right - 0.35 * win.width),
        int(win.bottom - 0.12 * win.height),
    )
    text_locations["crys_retry_box"] = (
        int(win.left + 0.85 * win.width),
        int(win.top + 0.81 * win.height),
        int(win.right - 0.05 * win.width),
        int(win.bottom - 0.12 * win.height),
    )
    text_locations["team_name"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.44 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.5 * win.height),
    )
    text_locations["crys_team_name"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.5 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.45 * win.height),
    )
    text_locations["party_box"] = (
        int(win.left + 0.29 * win.width),
        int(win.top + 0.44 * win.height),
        int(win.right - 0.65 * win.width),
        int(win.bottom - 0.5 * win.height),
    )
    text_locations["play_box"] = (
        int(win.left + 0.5 * win.width),
        int(win.top + 0.79 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.15 * win.height),
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["join_button_box"] = (
        int(win.left + 0.8 * win.width),
        int(win.top + 0.8 * win.height),
        int(win.right - 0.1 * win.width),
        int(win.bottom - 0.14 * win.height),
    )
    text_locations["battle_already_ended"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.45 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.45 * win.height),
    )
    text_locations["games_until_daily_bonus"] = (
        int(win.left + 0.64 * win.width),
        int(win.top + 0.74 * win.height),
        int(win.right - 0.34 * win.width),
        int(win.bottom - 0.21 * win.height),
    )
    text_locations["battle_already_ended_ok"] = (
        int(win.left + 0.5 * win.width),
        int(win.top + 0.75 * win.height),
    )
    text_locations["joined_battles"] = (
        int(win.left + 0.54 * win.width),
        int(win.top + 0.05 * win.height),
        int(win.right - 0.43 * win.width),
        int(win.bottom - 0.85 * win.height),
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
    text_locations["crys_next_team"] = (
        int(win.left + 0.28 * win.width),
        int(win.top + 0.62 * win.height),
    )
    text_locations["scroll_location"] = (
        win.left + 2 * win.width // 3,
        win.top + win.height // 4,
    )
    text_locations["join_lvl"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.22 * win.height),
        int(win.right - 0.24 * win.width),
        int(win.bottom - 0.74 * win.height),
    )
    text_locations["join_username_0"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.55 * win.height),
        int(win.right - 0.1 * win.width),
        int(win.bottom - 0.4 * win.height),
    )
    text_locations["join_username_1"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.64 * win.height),
        int(win.right - 0.1 * win.width),
        int(win.bottom - 0.31 * win.height),
    )
    text_locations["join_username_2"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.73 * win.height),
        int(win.right - 0.1 * win.width),
        int(win.bottom - 0.22 * win.height),
    )
    for i in range(3):
        text_locations[f"union_{i}"] = (
            int(text_locations[f"join_username_{i}"][0] + 0.03 * win.width),
            int(text_locations[f"join_username_{i}"][1] - 0.03 * win.height),
            int(text_locations[f"join_username_{i}"][2] - 0.08 * win.width),
            int(text_locations[f"join_username_{i}"][3] - 0.04 * win.height),
        )
    text_locations["round_box"] = (
        int(win.left + 0.54 * win.width),
        int(win.top + 0.5 * win.height),
        int(win.right - 0.34 * win.width),
        int(win.bottom - 0.45 * win.height),
    )
    text_locations["host_button"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["can_host_box"] = (
        int(win.left + 0.32 * win.width),
        int(win.top + 0.82 * win.height),
        int(win.right - 0.57 * win.width),
        int(win.bottom - 0.13 * win.height),
    )
    text_locations["in_progress_box"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.75 * win.height),
        int(win.right - 0.55 * win.width),
        int(win.bottom - 0.15 * win.height),
    )
    text_locations["tap_to_continue"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.85 * win.height),
        int(win.right - 0.4 * win.width),
        int(win.bottom - 0.05 * win.height),
    )
    text_locations["host_difficulty"] = (
        int(win.left + 0.73 * win.width),
        int(win.top + 0.17 * win.height),
        int(win.right - 0.22 * win.width),
        int(win.bottom - 0.78 * win.height),
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
        int(win.left + 0.45 * win.width),
        int(win.top + 0.08 * win.height),
        int(win.right - 0.53 * win.width),
        int(win.bottom - 0.87 * win.height),
    )
    text_locations["current_difficulty_single_digit"] = (
        text_locations["current_difficulty"][0] + 3,
        text_locations["current_difficulty"][1],
        text_locations["current_difficulty"][2] - 3,
        text_locations["current_difficulty"][3],
    )
    text_locations["crys_result_box"] = (
        int(win.left + 0.65 * win.width),
        int(win.top + 0.3 * win.height),
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.6 * win.height),
    )
    text_locations["crys_result_box2"] = (
        int(win.left + 0.65 * win.width),
        int(win.top + 0.1 * win.height),
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.8 * win.height),
    )
    text_locations["menu_button"] = (
        int(win.left + 0.95 * win.width),
        int(win.top + 0.08 * win.height),
    )
    text_locations["quests_button"] = (
        int(win.left + 0.9 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["upgrade_button"] = (
        int(win.left + 0.55 * win.width),
        int(win.top + 0.3 * win.height),
    )
    text_locations["raid_button"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.3 * win.height),
    )
    text_locations["crys_button"] = (
        int(win.left + 0.75 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["flame_button"] = (
        int(win.left + 0.1 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["aqua_button"] = (
        int(win.left + 0.25 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["forest_button"] = (
        int(win.left + 0.4 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["light_button"] = (
        int(win.left + 0.55 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["dark_button"] = (
        int(win.left + 0.7 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["void_button"] = (
        int(win.left + 0.85 * win.width),
        int(win.top + 0.5 * win.height),
    )
    text_locations["screen"] = (win.left, win.top, win.right, win.bottom)

    if DEBUG:
        img = ImageGrab.grab(text_locations["screen"])
        draw = ImageDraw.Draw(img)
        for name, coords in text_locations.items():
            if len(coords) == 4:
                x1, y1, x2, y2 = coords
                x1 -= win.left
                x2 -= win.left
                y1 -= win.top
                y2 -= win.top
                x = (x1 + x2) // 2
                y = (y1 + y2) // 2
                colour = "magenta"
                draw.rectangle((x1, y1, x2, y2), outline=colour, width=2)
            else:
                x, y = coords
                x -= win.left
                y -= win.top
                colour = "cyan"
                r = 5
                draw.ellipse((x - r, y - r, x + r, y + r), outline=colour, width=10)

            draw.text((x + 4, y + 4), name, fill=colour)
        img.save("debug/full_screencap.png")


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
                if (
                    DO_REFILL_LP
                    and not get_nrs_in_img("lp_refills_remaining").count("0") >= 2
                ):
                    click(
                        int(text_locations["host_back_box"][0]),
                        int(text_locations["host_back_box"][1]),
                    )
                else:
                    if LR_TO_CRYS_SWAP:
                        logger.info("Out of LP, swapping to crys farming")
                        click(*text_locations["menu_button"])
                        pyautogui.sleep(0.5)
                        click(*text_locations["menu_button"])
                        pyautogui.sleep(0.5)
                        click(*text_locations["quests_button"])
                        pyautogui.sleep(0.5)
                        click(*text_locations["upgrade_button"])
                        pyautogui.sleep(10)
                        click(*text_locations["crys_button"])
                        pyautogui.sleep(1.5)
                        click(*text_locations[f"{CRYS_ELEMENT}_button"])
                        pyautogui.sleep(0.5)
                        select_correct_team(CRYS_TEAM, True)
                        click(
                            int(text_locations["join_back_box"][0]),
                            int(text_locations["join_back_box"][1]),
                        )
                    else:
                        logger.info(
                            "Out of LP, swapping to crys farming is disabled. Quitting"
                        )
                        return
            case CurrentState.REFILL_QP:
                if (
                    DO_REFILL_QP
                    and not get_nrs_in_img("qp_refills_remaining").count("0") >= 2
                ):
                    click(
                        int(text_locations["host_back_box"][0]),
                        int(text_locations["host_back_box"][1]),
                    )
                else:
                    print("b")
                    if CRYS_TO_LR_SWAP:
                        logger.info("Out of QP, swapping to link raid")
                        click(
                            int(text_locations["host_screen_button"][0]),
                            int(text_locations["host_screen_button"][1]),
                        )
                        pyautogui.sleep(0.5)
                        click(*text_locations["play_button"])
                        pyautogui.sleep(5)
                        click(*text_locations["menu_button"])
                        pyautogui.sleep(0.5)
                        click(*text_locations["quests_button"])
                        pyautogui.sleep(0.5)
                        click(*text_locations["raid_button"])
                    else:
                        logger.info(
                            "Out of QP, swapping to link raid is disabled. Quitting"
                        )
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
            case CurrentState.CRYS_RETRY_SCREEN:
                click(
                    int(text_locations["crys_retry_box"][0]),
                    int(text_locations["crys_retry_box"][1]),
                )
            case CurrentState.CRYS_RESULTS_SCREEN:
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
            case CurrentState.EX_SCREEN:
                if CRYS_EX_SCREENSHOT:
                    img = ImageGrab.grab(text_locations["screen"])
                    os.makedirs("ex_drops", exist_ok=True)
                    img.save(
                        f"ex_drops/{datetime.today().strftime('%Y-%m-%dT%H-%M-%S')}.png"
                    )

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
