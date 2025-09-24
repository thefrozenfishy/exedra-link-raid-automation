import pytesseract
import pyautogui
import pydirectinput
import pygetwindow
import cv2
import os
import numpy as np
from PIL import ImageGrab, Image
from enum import Enum
import configparser

CONFIG_FILE = "link-raid-automation-settings.ini"

config = configparser.ConfigParser()
defaults = {
    "host_team": "LR Auto 8",
    "host_diff": "8",
    "join_team": "LR Auto 9-12",
    "join_diff": "9-12",
    "debug_mode": "false",
    "exe_name": "MadokaExedra",
    "max_scroll_attempts": "20",
}

config.read(CONFIG_FILE)
config["general"] = {
    **defaults,
    **(config["general"] if "general" in config else {}),
}

with open(CONFIG_FILE, "w", encoding="utf-8", newline="\n") as f:
    config.write(f)

DEBUG = config.getboolean("general", "debug_mode")
if DEBUG:
    os.makedirs("debug", exist_ok=True)

HOST_TEAM = config.get("general", "host_team").replace(" ", "").lower()
HOST_DIFF = config.getint("general", "host_diff")
JOIN_TEAM = config.get("general", "join_team").replace(" ", "").lower()
JOIN_DIFF = config.get("general", "join_diff")
if "-" in JOIN_DIFF:
    start, end = map(int, JOIN_DIFF.split("-"))
    LEVELS_TO_FIND = list(range(start, end + 1))
else:
    LEVELS_TO_FIND = [int(JOIN_DIFF)]

TARGET_WINDOW = config.get("general", "exe_name")
MAX_SCROLL_ATTEMPTS = config.getint("general", "max_scroll_attempts")


def get_game_window():
    wins = pygetwindow.getWindowsWithTitle(TARGET_WINDOW)
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def confirm_desired_difficulty(data, levels):
    for i, text in enumerate(data["text"]):
        if not text.strip():
            continue
        if (
            "lvl" in text.lower()
            and data["text"][i + 1].strip().isdigit()
            and int(data["text"][i + 1]) in levels
        ):
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i] + data["width"][i + 1],
                data["height"][i],
            )
            return x, y, w, h


def start_join():
    for attempt in range(MAX_SCROLL_ATTEMPTS):
        if DEBUG:
            print(f"Scroll attempt {attempt + 1:2}/{MAX_SCROLL_ATTEMPTS}")
        data = get_img("battle_box")
        match = confirm_desired_difficulty(data, LEVELS_TO_FIND)

        if match:
            x, y, w, h = match
            pyautogui.click(
                text_locations["battle_box"][0] + x + w // 2,
                text_locations["battle_box"][1] + y + h // 2,
            )
            pyautogui.sleep(0.5)

            pydirectinput.click(
                text_locations["join_button"][0], text_locations["join_button"][1]
            )
            pyautogui.sleep(2)
            return

        pyautogui.moveTo(
            text_locations["center_of_screen"][0],
            text_locations["center_of_screen"][1],
        )
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)

    # Refreshing
    pydirectinput.click(
        text_locations["refresh_button"][0], text_locations["refresh_button"][1]
    )


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    HOST_SCREEN = "HOST_SCREEN"
    HOME_SCREEN = "HOME_SCREEN"
    NO_ACTION = "NO_ACTION"
    RESULTS_SCREEN = "RESULTS_SCREEN"
    BACK_SCREEN = "BACK_SCREEN"
    PLAY_JOIN_SCREEN = "PLAY_JOIN_SCREEN"
    PLAY_HOST_SCREEN = "PLAY_HOST_SCREEN"


def get_img(cords: str):
    img = ImageGrab.grab(text_locations[cords])
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    gray = cv2.bitwise_not(gray)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    if DEBUG:
        img.save(f"debug/{cords}.png")
        Image.fromarray(gray).save(f"debug/{cords}_gray.png")
        print(cords, ">", data["text"])
    return data


def current_state() -> CurrentState:
    data = get_img("result_box")
    for text in data["text"]:
        if "lvl" in text.lower():
            return CurrentState.RESULTS_SCREEN

    data = get_img("battle_box")
    for text in data["text"]:
        if "lvl" in text.lower():
            return CurrentState.JOIN_SCREEN

    data = get_img("host_box")
    for text in data["text"]:
        if "ready" in text.lower():
            return CurrentState.HOST_SCREEN

    data = get_img("like_box")
    for text in data["text"]:
        if text.isdigit():
            return CurrentState.HOME_SCREEN

    data = get_img("back_box")
    for text in data["text"]:
        if "back" in text.lower():
            return CurrentState.BACK_SCREEN

    data = get_img("party_box")
    for text in data["text"]:
        if "party" in text.lower():
            data2 = get_img("play_box")
            for text in data2["text"]:
                if "play" in text.lower():
                    return CurrentState.PLAY_JOIN_SCREEN
            return CurrentState.PLAY_HOST_SCREEN

    return CurrentState.NO_ACTION


text_locations = {}


def setup_text_locations():
    win = get_game_window()
    try:
        win.activate()
    except Exception as e:
        print(
            f'Could not activate window: {e}.\nThis is not a major issue, just be sure that no application is hiding Exedra from view, \n\
The OCR has to "see" the content of the game to determine what to do.'
        )
    text_locations["result_box"] = (
        win.left + 0.23 * win.width,
        win.top + 0.795 * win.height,
        win.right - 0.725 * win.width,
        win.bottom - 0.172 * win.height,
    )
    text_locations["back_box"] = (
        win.left + 0.45 * win.width,
        win.top + 0.82 * win.height,
        win.right - 0.45 * win.width,
        win.bottom - 0.12 * win.height,
    )
    text_locations["team_name"] = (
        win.left + 0.4 * win.width,
        win.top + 0.45 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["party_box"] = (
        win.left + 0.29 * win.width,
        win.top + 0.45 * win.height,
        win.right - 0.65 * win.width,
        win.bottom - 0.5 * win.height,
    )
    text_locations["play_box"] = (
        win.left + 0.5 * win.width,
        win.top + 0.8 * win.height,
        win.right - 0.4 * win.width,
        win.bottom - 0.15 * win.height,
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
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
        int(win.top + 0.8 * win.height),
    )
    text_locations["host_screen_button"] = (
        int(win.left + 0.3 * win.width),
        int(win.top + 0.8 * win.height),
    )
    text_locations["next_team"] = (
        int(win.left + 0.28 * win.width),
        int(win.top + 0.58 * win.height),
    )
    text_locations["center_of_screen"] = (
        win.left + win.width // 2,
        win.top + win.height // 2,
    )
    text_locations["like_box"] = (
        win.left + 0.12 * win.width,
        win.top + 0.15 * win.height,
        win.right - 0.83 * win.width,
        win.bottom - 0.75 * win.height,
    )
    text_locations["battle_box"] = (
        win.left + 0.475 * win.width,
        win.top + 0.1 * win.height,
        win.right - 0.465 * win.width,
        win.bottom - 0.6 * win.height,
    )
    text_locations["host_box"] = (
        win.left + 0.73 * win.width,
        win.top + 0.81 * win.height,
        win.right - 0.15 * win.width,
        win.bottom - 0.13 * win.height,
    )


def select_correct_team(team_name):
    for _ in range(10):
        if team_name.lower() in "".join(get_img("team_name")["text"]).lower().replace(
            " ", ""
        ):
            return
        pydirectinput.click(
            text_locations["next_team"][0], text_locations["next_team"][1]
        )
        pyautogui.sleep(0.2)
    input(f'Could not find team named "{team_name}"')
    raise RuntimeError(f'Could not find team named "{team_name}"')


def main():
    while True:
        pyautogui.sleep(1)
        state = current_state()
        if DEBUG:
            print("Current State:", state.name)
        match state:
            case CurrentState.JOIN_SCREEN:
                start_join()
            case CurrentState.HOST_SCREEN:
                pydirectinput.click(
                    int(text_locations["host_box"][0]),
                    int(text_locations["host_box"][1]),
                )
            case CurrentState.HOME_SCREEN:
                # TODO: Do host if not done hosting
                # pydirectinput.click(text_locations["host_screen_button"][0], text_locations["host_screen_button"][1])
                pydirectinput.click(
                    text_locations["join_screen_button"][0],
                    text_locations["join_screen_button"][1],
                )
            case CurrentState.PLAY_JOIN_SCREEN:
                select_correct_team(JOIN_TEAM)
                print("Joining a game...")
                pydirectinput.click(
                    text_locations["play_button"][0], text_locations["play_button"][1]
                )
                pyautogui.sleep(2)
            case CurrentState.PLAY_HOST_SCREEN:
                select_correct_team(HOST_TEAM)
                print("Hosting a game...")
                pydirectinput.click(
                    text_locations["play_button"][0], text_locations["play_button"][1]
                )
                pyautogui.sleep(2)
            case CurrentState.NO_ACTION:
                pyautogui.sleep(5)
                # No need to ping the process that much while in battle.
            case CurrentState.RESULTS_SCREEN:
                pydirectinput.click(
                    int(text_locations["result_box"][0]),
                    int(text_locations["result_box"][1]),
                )
            case CurrentState.BACK_SCREEN:
                pydirectinput.click(
                    int(text_locations["back_box"][0]),
                    int(text_locations["back_box"][1]),
                )
                pyautogui.sleep(2)


if __name__ == "__main__":
    setup_text_locations()
    main()
