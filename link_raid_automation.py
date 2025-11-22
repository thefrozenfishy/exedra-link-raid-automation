import colorsys
import configparser
import logging
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
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
import win32gui
from Levenshtein import distance as lev_distance
from PIL import Image, ImageDraw, ImageGrab
from requests import get

pyautogui.FAILSAFE = False
pydirectinput.FAILSAFE = False
__version__ = "vDEV"

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
    "love_everyone": "true",
    "automatically_turn_on_auto": "false",
    "boss": "Wheel",
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
LEVELS_TO_FIND = []
for diffs in JOIN_DIFF.split(","):
    if "-" in diffs:
        start, end = map(int, diffs.split("-"))
        LEVELS_TO_FIND += list(range(start, end + 1))
    else:
        LEVELS_TO_FIND.append(int(diffs))

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

DO_LOVE = ini_config.getboolean("general", "love_everyone")
DO_HOST = ini_config.getboolean("general", "auto_host")
ENABLE_AUTO = ini_config.getboolean("general", "automatically_turn_on_auto")
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
CURRENT_BOSS = ini_config.get("general", "boss").strip().lower()

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

running = True


def toggle_running():
    global running
    if running:
        logger.info("Pausing")
    else:
        logger.info("Resuming")
    running = not running


def take_debug_screencap():
    client_left = text_locations["screen"][0]
    client_top = text_locations["screen"][1]
    img = ImageGrab.grab(text_locations["screen"])
    draw = ImageDraw.Draw(img)
    for name, coords in text_locations.items():
        if len(coords) == 4:
            x1, y1, x2, y2 = coords
            x1 -= client_left
            x2 -= client_left
            y1 -= client_top
            y2 -= client_top
            x = (x1 + x2) // 2
            y = (y1 + y2) // 2
            colour = "magenta"
            if name.startswith("crys_"):
                colour = "green"
            draw.rectangle((x1, y1, x2, y2), outline=colour, width=2)
        else:
            x, y = coords
            x -= client_left
            y -= client_top
            colour = "cyan"
            if name.startswith("crys_"):
                colour = "green"
            r = 5
            draw.ellipse((x - r, y - r, x + r, y + r), outline=colour, width=10)

        draw.text((x + 4, y + 4), name, fill=colour)
    img.save("debug/full_screencap.png")

    get_text_in_img("screen")


keyboard.add_hotkey("ctrl+shift+q", lambda: os._exit(0))
keyboard.add_hotkey("ctrl+shift+e", toggle_running)
keyboard.add_hotkey("ctrl+shift+p", take_debug_screencap)

log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)
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

TESSARACT_WHITELIST = "--psm 6 -c tessedit_char_whitelist={}"


def is_close_name(name, candidates):
    if len(name) < 3:
        return False
    for cand in candidates:
        max_dist = 1 if len(cand) <= 7 else 2
        if lev_distance(name, cand) > max_dist:
            continue
        if SequenceMatcher(None, name, cand).ratio() < 0.85:
            continue
        return True
    return False


def check_git_version_match():
    git_version = get(
        "https://api.github.com/repos/thefrozenfishy/exedra-link-raid-automation/releases/latest",
        timeout=10,
    )
    if git_version.status_code == 200:
        data = git_version.json()
        version = data["tag_name"].lstrip("version-")
        if f"v{version}" != __version__:
            logger.warning(
                "New version available: v%s, you are on %s", version, __version__
            )


def get_game_window():
    wins = pygetwindow.getWindowsWithTitle(TARGET_WINDOW)
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def normalize_1_and_0(s: str) -> str:
    return (
        s.replace("i", "1")
        .replace("I", "1")
        .replace("l", "1")
        .replace("]", "1")
        .replace("[", "1")
        .replace("O", "0")
        .replace("o", "0")
    )


def get_text_in_img(cords: str, config="", make_bw=False) -> str:
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
        img.save(f"debug/{cords}.png")
        if make_bw:
            Image.fromarray(img_data).save(f"debug/{cords}_bw.png")
        logger.debug("%s > %s", cords, data["text"])
    return re.sub(r"[^A-Za-z0-9]", "", "".join(data["text"]).lower().replace(" ", ""))


def get_nrs_in_img(cords: str) -> str:
    return normalize_1_and_0(
        get_text_in_img(cords, config=TESSARACT_WHITELIST.format("0oO123456789ilI"))
    )


def get_color_diff_range(offset: str) -> tuple[float, float, float]:
    mid_x = (
        text_locations[offset][0]
        + abs(text_locations[offset][0] - text_locations[offset][2]) // 2
    )
    mid_y = (
        text_locations[offset][1]
        + abs(text_locations[offset][1] - text_locations[offset][3]) // 2
    )
    colour_img = ImageGrab.grab(
        (
            mid_x,
            mid_y - 10,
            mid_x + 10,
            mid_y + 5,
        )
    )
    arr = np.array(colour_img).astype(float) / 255.0
    avg_rgb = arr.mean(axis=(0, 1))  # [R, G, B] normalized
    r, g, b = avg_rgb

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360

    return h, s, v


def translate_hsv_to_difficulty_range(h, s, v) -> set[int]:
    if 230 < h < 250 and s < 0.05:
        return set(range(17, 21))  # White
    if (30 < h < 70 and s < 0.15 and 0.65 > v > 0.35) or (
        h < 50 and s < 0.1 and v < 0.3
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
    eligable_nrs = translate_hsv_to_difficulty_range(*get_color_diff_range("join_lvl"))
    eligable_nrs_str = "".join(set("".join(map(str, eligable_nrs))))
    if 1 in eligable_nrs:
        eligable_nrs_str += "ilI"
    logger.debug("eligible NRs %s", eligable_nrs_str)
    lvl = normalize_1_and_0(
        get_text_in_img(
            "join_lvl",
            config=TESSARACT_WHITELIST.format("Lvl" + eligable_nrs_str),
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
    if JOIN_FRIENDS or JOIN_COMMUNITY:
        for i in range(3):
            is_union = "union" in get_text_in_img(f"union_{i}").lower()
            if is_union and JOIN_FRIENDS:
                logger.info("Joining union member")
                return True

            username = get_text_in_img(
                f"player_{'with' if is_union else 'without'}_union_{i}"
            )
            logger.debug("User%d was found to be '%s'", i, username)

            if not username.strip():
                break
            if JOIN_FRIENDS and is_close_name(username, friends):
                logger.info("Joining friend %s", username)
                return True
            if JOIN_COMMUNITY and is_close_name(username, community):
                logger.info("Joining community member %s", username)
                return True
    if ONLY_JOIN_FRIENDS_AND_COMMUNITY:
        return False
    if lvl in LEVELS_TO_FIND:
        return True
    return False


def select_correct_team(team_name, is_crys):
    for _ in range(100):
        if team_name.lower() in get_text_in_img(
            "crys_team_name" if is_crys else "team_name"
        ):
            return
        click(*text_locations["crys_next_team" if is_crys else "next_team"])
        pyautogui.sleep(0.2)

    input(f'Your team "{team_name}" could not be found! Make sure it exists.')
    raise RuntimeError(f'Could not find team named "{team_name}"')


def start_play():
    single_digit_diff = get_nrs_in_img("current_difficulty_single_digit")
    multi_digit_diff = get_nrs_in_img("current_difficulty")
    diff = 0
    if single_digit_diff.isdigit() and int(single_digit_diff) < 10:
        diff = int(single_digit_diff)
    elif multi_digit_diff.isdigit() and int(multi_digit_diff) >= 10:
        diff = int(multi_digit_diff) % 100
    select_correct_team(teams.get(diff, default_team), is_crys=False)
    logger.debug(
        "Starting play at difficulty %d using %s", diff, teams.get(diff, default_team)
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
        eligable_nrs = translate_hsv_to_difficulty_range(
            *get_color_diff_range("host_difficulty")
        )
        eligable_nrs_str = "".join(set("".join(map(str, eligable_nrs))))
        if 1 in eligable_nrs:
            eligable_nrs_str += "ilI]["
        logger.debug("eligible host NRs %s", eligable_nrs_str)
        lvl = normalize_1_and_0(
            get_text_in_img(
                "host_difficulty",
                config=TESSARACT_WHITELIST.format(eligable_nrs_str),
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
    return v >= 0.3


def claim_battles():
    current_battles = get_nrs_in_img("joined_battles")
    if not (current_battles.isdigit() and int(current_battles) <= 3):
        for _ in range(60):
            if "end" in get_text_in_img("join_button_box"):
                click(*text_locations["join_button"])
                return

            pydirectinput.click(*text_locations["scroll_location"])
            pyautogui.scroll(-1)
            pyautogui.scroll(-1)
            pyautogui.scroll(-1)

            if is_scroll_at_bottom():
                break

    click(*text_locations["join_battles_tab"])


def start_join():
    global join_nr

    current_battles = get_nrs_in_img("joined_battles")
    if current_battles.isdigit() and int(current_battles) == 10:
        click(*text_locations["joined_battles_tab"])
        return
    for _ in range(60):
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

        if is_scroll_at_bottom():
            break

    click(*text_locations["refresh_button"])


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    NO_JOINS_FOUND = "NO_JOINS_FOUND"
    JOINED_BATTLES_SCREEN = "JOINED_BATTLES_SCREEN"
    HOST_SCREEN = "HOST_SCREEN"
    HOME_SCREEN_CAN_HOST = "HOME_SCREEN_CAN_HOST"
    HOME_SCREEN_CANNOT_HOST = "HOME_SCREEN_CANNOT_HOST"
    NO_ACTION = "NO_ACTION"
    RESULTS_SCREEN = "RESULTS_SCREEN"
    CRYS_RESULTS_SCREEN = "CRYS_RESULTS_SCREEN"
    CRYS_RETRY_SCREEN = "CRYS_RETRY_SCREEN"
    CRYS_FAILED = "CRYS_FAILED"
    JOIN_BACK_SCREEN = "JOIN_BACK_SCREEN"
    HOST_BACK_SCREEN = "HOST_BACK_SCREEN"
    PLAY_JOIN_SCREEN = "PLAY_JOIN_SCREEN"
    PLAY_HOST_SCREEN = "PLAY_HOST_SCREEN"
    CRYS_SELECT_SCREEN = "CRYS_SELECT_SCREEN"
    CRYS_TEAM_SELECT_SCREEN = "CRYS_TEAM_SELECT_SCREEN"
    REFILL_LP = "REFILL_LP"
    REFILL_QP = "REFILL_QP"
    DAILY_BONUS_COUNTER = "DAILY_BONUS_COUNTER"
    DAILY_BONUS = "DAILY_BONUS"
    BATTLE_ALREADY_ENDED = "BATTLE_ALREADY_ENDED"
    CURRENTLY_HOSTING_SCREEN = "CURRENTLY_HOSTING_SCREEN"
    EX_SCREEN = "EX_SCREEN"
    BATTLE_ON_MANUAL = "BATTLE_ON_MANUAL"
    CONTINUE = "CONTINUE"


def current_state() -> CurrentState:
    if "1v1" in normalize_1_and_0(get_text_in_img("result_box")):
        return CurrentState.RESULTS_SCREEN

    if "retry" in normalize_1_and_0(get_text_in_img("crys_retry_box")):
        return CurrentState.CRYS_RETRY_SCREEN

    if "bta1ned" in normalize_1_and_0(
        get_text_in_img("crys_result_box")
    ) or "esu1t" in normalize_1_and_0(get_text_in_img("crys_result_box2")):
        return CurrentState.CRYS_RESULTS_SCREEN

    if "batt1ehas" in normalize_1_and_0(get_text_in_img("battle_already_ended")):
        return CurrentState.BATTLE_ALREADY_ENDED

    text = normalize_1_and_0(get_text_in_img("join_button_box"))
    if "j01n" in text:
        return CurrentState.JOIN_SCREEN
    if "etreat" in text or "ended" in text:
        return CurrentState.JOINED_BATTLES_SCREEN

    text = normalize_1_and_0(get_text_in_img("daily_bonus_box"))
    if "da11y" in text:
        if "r1ng" in text:
            return CurrentState.REFILL_LP
        if "cube" in text:
            return CurrentState.REFILL_QP
        return CurrentState.DAILY_BONUS_COUNTER

    if "fa11ed" in text:
        return CurrentState.CRYS_FAILED

    if "round" in get_text_in_img("round_box"):
        return CurrentState.HOST_SCREEN

    if "back" in get_text_in_img("join_back_box"):
        return CurrentState.JOIN_BACK_SCREEN

    if "back" in get_text_in_img("host_back_box"):
        return CurrentState.HOST_BACK_SCREEN

    text = normalize_1_and_0(get_text_in_img("party_box"))
    if "party" in text:
        text2 = normalize_1_and_0(get_text_in_img("play_box"))
        if "p1ay" in text2.lower():
            return CurrentState.PLAY_JOIN_SCREEN
        return CurrentState.PLAY_HOST_SCREEN

    in_progress_text = normalize_1_and_0(get_text_in_img("in_progress_box"))
    if "v1ewresu1ts" in in_progress_text:
        return CurrentState.HOME_SCREEN_CAN_HOST

    text = normalize_1_and_0(get_text_in_img("can_host_box"))
    if "p1ay" in text:
        if not DO_HOST:
            return CurrentState.HOME_SCREEN_CANNOT_HOST
        if "1n" in in_progress_text:
            return CurrentState.HOME_SCREEN_CANNOT_HOST
        if "0" in text:
            return CurrentState.HOME_SCREEN_CANNOT_HOST
        return CurrentState.HOME_SCREEN_CAN_HOST

    if "c0nt1nue" in normalize_1_and_0(get_text_in_img("tap_to_continue")):
        return CurrentState.CONTINUE

    if "retreat" in get_text_in_img("retreat_box"):
        return CurrentState.CURRENTLY_HOSTING_SCREEN

    if "c0nt" in normalize_1_and_0(get_text_in_img("crys_ex_continue_box")):
        return CurrentState.EX_SCREEN

    if "next" in get_text_in_img("next_box"):
        if "c0nt1n" in normalize_1_and_0(get_text_in_img("join_back_box")):
            return CurrentState.DAILY_BONUS
        return CurrentState.RESULTS_SCREEN

    if "backup" in get_text_in_img("no_join_available"):
        return CurrentState.NO_JOINS_FOUND

    if "rysta" in get_text_in_img("crys_quest_team_select"):
        return CurrentState.CRYS_TEAM_SELECT_SCREEN

    if "xtra" in get_text_in_img("crys_diff", make_bw=True):
        return CurrentState.CRYS_SELECT_SCREEN

    *_, v = get_color_diff_range("current_play_mode")
    logger.debug("Current play mode v=%.2f", v)
    if 0.38 < v < 0.4:
        return CurrentState.BATTLE_ON_MANUAL

    return CurrentState.NO_ACTION


text_locations = {}


def love_everyone():
    if not DO_LOVE:
        return
    for i in range(6):
        click(*text_locations[f"love_button_{i}"])
        pyautogui.sleep(2.5)


def click_box(x1: float | int, y1: float | int, x2: float | int, y2: float | int):
    click((x1 + x2) / 2, (y1 + y2) / 2)


def click(x: float | int, y: float | int):
    curr = pyautogui.position()
    pydirectinput.click(int(x), int(y))
    pyautogui.moveTo(curr)


def setup_text_locations(first_time: bool):
    win = get_game_window()
    hwnd = win._hWnd
    client_rect = win32gui.GetClientRect(hwnd)
    left_top = win32gui.ClientToScreen(hwnd, (0, 0))
    right_bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
    client_left, client_top = left_top
    client_right, client_bottom = right_bottom

    client_width = client_right - client_left
    client_height = client_bottom - client_top

    logger.debug("Client area resolution is %dx%d", client_width, client_height)

    if first_time:
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
        int(client_left + 0.23 * client_width),
        int(client_top + 0.785 * client_height),
        int(client_right - 0.725 * client_width),
        int(client_bottom - 0.172 * client_height),
    )
    text_locations["crys_diff"] = (
        int(client_left + 0.23 * client_width),
        int(client_top + 0.825 * client_height),
        int(client_right - 0.715 * client_width),
        int(client_bottom - 0.13 * client_height),
    )
    text_locations["scroll_bar"] = (
        int(client_left + 0.685 * client_width),
        int(client_top + 0.85 * client_height),
        int(client_right - 0.305 * client_width),
        int(client_bottom - 0.12 * client_height),
    )
    text_locations["retreat_box"] = (
        int(client_left + 0.78 * client_width),
        int(client_top + 0.83 * client_height),
        int(client_right - 0.12 * client_width),
        int(client_bottom - 0.1 * client_height),
    )
    text_locations["crys_ex_continue_box"] = (
        int(client_left + 0.75 * client_width),
        int(client_top + 0.85 * client_height),
        int(client_right - 0.15 * client_width),
        int(client_bottom - 0.1 * client_height),
    )
    text_locations["daily_bonus_box"] = (
        int(client_left + 0.3 * client_width),
        int(client_top + 0.1 * client_height),
        int(client_right - 0.3 * client_width),
        int(client_bottom - 0.7 * client_height),
    )
    text_locations["lp_refills_remaining"] = (
        int(client_left + 0.5 * client_width),
        int(client_top + 0.55 * client_height),
        int(client_right - 0.45 * client_width),
        int(client_bottom - 0.4 * client_height),
    )
    text_locations["crys_qp_refills_remaining"] = (
        int(client_left + 0.5 * client_width),
        int(client_top + 0.55 * client_height),
        int(client_right - 0.45 * client_width),
        int(client_bottom - 0.35 * client_height),
    )
    text_locations["daily_reward_pic_box"] = (
        int(client_left + 0.35 * client_width),
        int(client_top + 0.35 * client_height),
        int(client_right - 0.35 * client_width),
        int(client_bottom - 0.4 * client_height),
    )
    text_locations["join_back_box"] = (
        int(client_left + 0.45 * client_width),
        int(client_top + 0.81 * client_height),
        int(client_right - 0.45 * client_width),
        int(client_bottom - 0.12 * client_height),
    )
    text_locations["host_back_box"] = (
        int(client_left + 0.55 * client_width),
        int(client_top + 0.81 * client_height),
        int(client_right - 0.35 * client_width),
        int(client_bottom - 0.12 * client_height),
    )
    text_locations["crys_retry_box"] = (
        int(client_left + 0.87 * client_width),
        int(client_top + 0.81 * client_height),
        int(client_right - 0.06 * client_width),
        int(client_bottom - 0.12 * client_height),
    )
    text_locations["team_name"] = (
        int(client_left + 0.4 * client_width),
        int(client_top + 0.44 * client_height),
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.5 * client_height),
    )
    text_locations["crys_team_name"] = (
        int(client_left + 0.46 * client_width),
        int(client_top + 0.45 * client_height),
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.45 * client_height),
    )
    text_locations["party_box"] = (
        int(client_left + 0.29 * client_width),
        int(client_top + 0.44 * client_height),
        int(client_right - 0.65 * client_width),
        int(client_bottom - 0.5 * client_height),
    )
    text_locations["play_box"] = (
        int(client_left + 0.5 * client_width),
        int(client_top + 0.79 * client_height),
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.15 * client_height),
    )
    text_locations["join_button"] = (
        int(client_right - 0.15 * client_width),
        int(client_bottom - 0.18 * client_height),
    )
    text_locations["join_button_box"] = (
        int(client_left + 0.8 * client_width),
        int(client_top + 0.8 * client_height),
        int(client_right - 0.1 * client_width),
        int(client_bottom - 0.14 * client_height),
    )
    text_locations["battle_already_ended"] = (
        int(client_left + 0.4 * client_width),
        int(client_top + 0.45 * client_height),
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.45 * client_height),
    )
    text_locations["games_until_daily_bonus"] = (
        int(client_left + 0.64 * client_width),
        int(client_top + 0.74 * client_height),
        int(client_right - 0.34 * client_width),
        int(client_bottom - 0.21 * client_height),
    )
    text_locations["battle_already_ended_ok"] = (
        int(client_left + 0.5 * client_width),
        int(client_top + 0.75 * client_height),
    )
    text_locations["joined_battles"] = (
        int(client_left + 0.54 * client_width),
        int(client_top + 0.02 * client_height),
        int(client_right - 0.43 * client_width),
        int(client_bottom - 0.92 * client_height),
    )
    text_locations["join_battles_tab"] = (
        int(client_left + 0.2 * client_width),
        int(client_top + 0.2 * client_height),
    )
    text_locations["joined_battles_tab"] = (
        int(client_left + 0.2 * client_width),
        int(client_top + 0.3 * client_height),
    )
    text_locations["play_button"] = (
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.18 * client_height),
    )
    text_locations["refresh_button"] = (
        int(client_left + 0.31 * client_width),
        int(client_top + 0.03 * client_height),
    )
    text_locations["join_screen_button"] = (
        int(client_left + 0.7 * client_width),
        int(client_top + 0.82 * client_height),
    )
    text_locations["host_screen_button"] = (
        int(client_left + 0.3 * client_width),
        int(client_top + 0.8 * client_height),
    )
    text_locations["next_team"] = (
        int(client_left + 0.28 * client_width),
        int(client_top + 0.58 * client_height),
    )
    text_locations["crys_next_team"] = (
        int(client_left + 0.28 * client_width),
        int(client_top + 0.62 * client_height),
    )
    text_locations["scroll_location"] = (
        client_left + 2 * client_width // 3,
        client_top + client_height // 4,
    )
    text_locations["join_lvl"] = (
        int(client_left + 0.705 * client_width),
        int(client_top + 0.18 * client_height),
        int(client_right - 0.235 * client_width),
        int(client_bottom - 0.78 * client_height),
    )
    text_locations["no_join_available"] = (
        int(client_left + 0.5 * client_width),
        int(client_top + 0.42 * client_height),
        int(client_right - 0.3 * client_width),
        int(client_bottom - 0.48 * client_height),
    )
    text_locations["union_0"] = (
        int(client_left + 0.76 * client_width),
        int(client_top + 0.51 * client_height),
        int(client_right - 0.175 * client_width),
        int(client_bottom - 0.455 * client_height),
    )
    text_locations["union_1"] = (
        int(client_left + 0.76 * client_width),
        int(client_top + 0.60 * client_height),
        int(client_right - 0.175 * client_width),
        int(client_bottom - 0.365 * client_height),
    )
    text_locations["union_2"] = (
        int(client_left + 0.76 * client_width),
        int(client_top + 0.69 * client_height),
        int(client_right - 0.175 * client_width),
        int(client_bottom - 0.275 * client_height),
    )
    for i in range(3):
        text_locations[f"player_with_union_{i}"] = (
            int(text_locations[f"union_{i}"][0] - 0.02 * client_width),
            int(text_locations[f"union_{i}"][1] + 0.025 * client_height),
            int(text_locations[f"union_{i}"][2] + 0.15 * client_width),
            int(text_locations[f"union_{i}"][3] + 0.05 * client_height),
        )
        text_locations[f"player_without_union_{i}"] = (
            int(text_locations[f"union_{i}"][0] - 0.02 * client_width),
            int(text_locations[f"union_{i}"][1] + 0.01 * client_height),
            int(text_locations[f"union_{i}"][2] + 0.15 * client_width),
            int(text_locations[f"union_{i}"][3] + 0.03 * client_height),
        )

    text_locations["round_box"] = (
        int(client_left + 0.54 * client_width),
        int(client_top + 0.48 * client_height),
        int(client_right - 0.34 * client_width),
        int(client_bottom - 0.47 * client_height),
    )
    text_locations["host_button"] = (
        int(client_left + 0.73 * client_width),
        int(client_top + 0.8 * client_height),
    )
    text_locations["can_host_box"] = (
        int(client_left + 0.32 * client_width),
        int(client_top + 0.82 * client_height),
        int(client_right - 0.57 * client_width),
        int(client_bottom - 0.13 * client_height),
    )
    text_locations["in_progress_box"] = (
        int(client_left + 0.3 * client_width),
        int(client_top + 0.75 * client_height),
        int(client_right - 0.55 * client_width),
        int(client_bottom - 0.15 * client_height),
    )
    text_locations["tap_to_continue"] = (
        int(client_left + 0.4 * client_width),
        int(client_top + 0.85 * client_height),
        int(client_right - 0.4 * client_width),
        int(client_bottom - 0.05 * client_height),
    )
    text_locations["host_difficulty"] = (
        int(client_left + 0.73 * client_width),
        int(client_top + 0.13 * client_height),
        int(client_right - 0.18 * client_width),
        int(client_bottom - 0.83 * client_height),
    )
    text_locations["host_decrement"] = (
        int(client_left + 0.64 * client_width),
        int(client_top + 0.19 * client_height),
    )
    text_locations["host_increment"] = (
        int(client_left + 0.84 * client_width),
        int(client_top + 0.19 * client_height),
    )
    match CURRENT_BOSS:
        case "sandbox":
            diff_left = 0.45
            diff_right = 0.53
        case "spindle":
            diff_left = 0.452
            diff_right = 0.525
        case "horse":
            diff_left = 0.387
            diff_right = 0.59
        case "wheel":
            diff_left = 0.36
            diff_right = 0.62
        case _:
            logger.error("Unknown boss '%s', using Wheel coords", CURRENT_BOSS)
            diff_left = 0.36
            diff_right = 0.62
    text_locations["current_difficulty"] = (
        int(client_left + diff_left * client_width),
        int(client_top + 0.04 * client_height),
        int(client_right - diff_right * client_width),
        int(client_bottom - 0.91 * client_height),
    )
    text_locations["current_difficulty_single_digit"] = (
        text_locations["current_difficulty"][0] + 3,
        text_locations["current_difficulty"][1],
        text_locations["current_difficulty"][2] - 3,
        text_locations["current_difficulty"][3],
    )
    text_locations["crys_result_box"] = (
        int(client_left + 0.65 * client_width),
        int(client_top + 0.3 * client_height),
        int(client_right - 0.15 * client_width),
        int(client_bottom - 0.6 * client_height),
    )
    text_locations["crys_result_box2"] = (
        int(client_left + 0.65 * client_width),
        int(client_top + 0.1 * client_height),
        int(client_right - 0.15 * client_width),
        int(client_bottom - 0.8 * client_height),
    )
    text_locations["crys_quest_team_select"] = (
        int(client_left + 0.36 * client_width),
        int(client_top + 0.04 * client_height),
        int(client_right - 0.36 * client_width),
        int(client_bottom - 0.91 * client_height),
    )
    text_locations["current_play_mode"] = (
        int(client_left + 0.83 * client_width),
        int(client_top + 0.06 * client_height),
        int(client_right - 0.165 * client_width),
        int(client_bottom - 0.93 * client_height),
    )
    text_locations["menu_button"] = (
        int(client_left + 0.95 * client_width),
        int(client_top + 0.08 * client_height),
    )
    text_locations["quests_button"] = (
        int(client_left + 0.9 * client_width),
        int(client_top + 0.8 * client_height),
    )
    text_locations["upgrade_button"] = (
        int(client_left + 0.55 * client_width),
        int(client_top + 0.3 * client_height),
    )
    text_locations["raid_button"] = (
        int(client_left + 0.7 * client_width),
        int(client_top + 0.3 * client_height),
    )
    text_locations["hosting_back_button"] = (
        int(client_left + 0.05 * client_width),
        int(client_top + 0.05 * client_height),
    )
    text_locations["crys_button"] = (
        int(client_left + 0.75 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_flame_button"] = (
        int(client_left + 0.1 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_aqua_button"] = (
        int(client_left + 0.25 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_forest_button"] = (
        int(client_left + 0.4 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_light_button"] = (
        int(client_left + 0.55 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_dark_button"] = (
        int(client_left + 0.7 * client_width),
        int(client_top + 0.5 * client_height),
    )
    text_locations["crys_void_button"] = (
        int(client_left + 0.85 * client_width),
        int(client_top + 0.5 * client_height),
    )
    for i in range(3):
        text_locations[f"love_button_{i*2}"] = (
            int(client_left + 0.47 * client_width),
            int(client_top + (0.3 + 0.2 * i) * client_height),
        )
        text_locations[f"love_button_{i*2+1}"] = (
            int(client_left + 0.93 * client_width),
            int(client_top + (0.3 + 0.2 * i) * client_height),
        )
    text_locations["next_box"] = (
        int(client_left + 0.95 * client_width),
        int(client_top + 0.95 * client_height),
        int(client_right),
        int(client_bottom),
    )
    text_locations["screen"] = (client_left, client_top, client_right, client_bottom)

    if DEBUG and first_time:
        take_debug_screencap()


def main():
    logger.info(
        "starting with config: %s",
        {**dict(ini_config["general"]), **{"lvls": str(LEVELS_TO_FIND)}},
    )
    logger.info(
        "Considering %s friends and %s community members",
        len(friends) if JOIN_FRIENDS else "no",
        len(community) if JOIN_COMMUNITY else "no",
    )
    logger.info("Press Ctrl+Shift+Q to terminate the program.")
    logger.info("Press Ctrl+Shift+E to pause the program.")
    logger.debug("Current version %s", __version__)
    check_git_version_match()
    i = 0
    while True:
        pyautogui.sleep(1)
        if not running:
            continue
        if i % 10 == 0:
            setup_text_locations(i == 0)
        i += 1
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
                    else:
                        logger.info(
                            "Out of LP, swapping to crys farming is disabled. Quitting"
                        )
                        return
            case CurrentState.CRYS_SELECT_SCREEN:
                click(*text_locations[f"crys_{CRYS_ELEMENT}_button"])
            case CurrentState.CRYS_TEAM_SELECT_SCREEN:
                select_correct_team(CRYS_TEAM, True)
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
            case CurrentState.REFILL_QP:
                if (
                    DO_REFILL_QP
                    and not get_nrs_in_img("crys_qp_refills_remaining").count("0") >= 2
                ):
                    click(
                        int(text_locations["host_back_box"][0]),
                        int(text_locations["host_back_box"][1]),
                    )
                else:
                    print("b")
                    if CRYS_TO_LR_SWAP:
                        logger.info("Out of QP, swapping to link raid")
                        click(*text_locations["host_screen_button"])
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
            case CurrentState.BATTLE_ON_MANUAL:
                if ENABLE_AUTO:
                    click_box(*text_locations["current_play_mode"])
                    click_box(*text_locations["current_play_mode"])
            case CurrentState.PLAY_JOIN_SCREEN:
                logger.info("Joining a game...")
                start_play()
            case CurrentState.PLAY_HOST_SCREEN:
                logger.info("Hosting a game...")
                start_play()
            case CurrentState.NO_ACTION:
                pyautogui.sleep(5)
            case CurrentState.CRYS_FAILED:
                click(*text_locations["host_screen_button"])
            case CurrentState.RESULTS_SCREEN:
                click(
                    int(text_locations["join_back_box"][2]),
                    int(text_locations["join_back_box"][3]),
                )
            case CurrentState.CRYS_RETRY_SCREEN:
                click(
                    int(text_locations["crys_retry_box"][0]),
                    int(text_locations["crys_retry_box"][1]),
                )
            case CurrentState.CRYS_RESULTS_SCREEN:
                click(
                    int(text_locations["join_back_box"][2]),
                    int(text_locations["join_back_box"][3]),
                )
            case CurrentState.JOIN_BACK_SCREEN:
                love_everyone()
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
                pyautogui.sleep(2)
            case CurrentState.HOST_BACK_SCREEN:
                love_everyone()
                click(
                    int(text_locations["host_back_box"][0]),
                    int(text_locations["host_back_box"][1]),
                )
            case CurrentState.CONTINUE:
                click(
                    int(text_locations["join_back_box"][0]),
                    int(text_locations["join_back_box"][1]),
                )
            case CurrentState.CURRENTLY_HOSTING_SCREEN:
                click(*text_locations["hosting_back_button"])
            case CurrentState.NO_JOINS_FOUND:
                click(*text_locations["refresh_button"])
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
