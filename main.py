import pytesseract
import pyautogui
import pydirectinput
import pygetwindow
import cv2
import numpy as np
from PIL import ImageGrab
from enum import Enum

# Config
TARGET_WINDOW = "MadokaExedra"
LEVELS_TO_FIND = [9, 10, 11, 12]
MAX_SCROLL_ATTEMPTS = 20


def get_game_window():
    wins = [w for w in pygetwindow.getWindowsWithTitle(TARGET_WINDOW)]
    if not wins:
        raise RuntimeError("Game window not found")
    return wins[0]


def find_levels(img, levels):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    for i, text in enumerate(data["text"]):
        if not text.strip():
            continue
        if (
            text == "Lvl."
            and data["text"][i + 1].isdigit()
            and int(data["text"][i + 1]) in levels
        ):
            lvl = int(data["text"][i + 1])
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i] + data["width"][i + 1],
                data["height"][i],
            )
            return lvl, x, y, w, h
    return None


def start_join():
    for attempt in range(MAX_SCROLL_ATTEMPTS):
        img = ImageGrab.grab(text_locations["battle_box"])
        match = find_levels(img, LEVELS_TO_FIND)

        if match:
            lvl, x, y, w, h = match
            print(f"Found Lvl {lvl} at ({x}, {y})")
            click_x = text_locations["battle_box"][0] + x + w // 2
            click_y = text_locations["battle_box"][1] + y + h // 2
            pyautogui.click(click_x, click_y)
            pyautogui.sleep(0.5)
            pydirectinput.click(
                text_locations["join_button"][0], text_locations["join_button"][1]
            )
            pyautogui.sleep(1)
            pydirectinput.click(
                text_locations["play_button"][0], text_locations["play_button"][1]
            )

            return
        print("Not found, scrolling...")
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


def find_finish():
    pydirectinput.click(
        int(text_locations["result_box"][0]), int(text_locations["result_box"][1])
    )
    pyautogui.sleep(1)
    pydirectinput.click(
        text_locations["back_button"][0], text_locations["back_button"][1]
    )


def start_host():
    pass


class CurrentState(Enum):
    JOIN_SCREEN = "JOIN_SCREEN"
    HOME_SCREEN = "HOME_SCREEN"
    BATTLE_SCREEN = "BATTLE_SCREEN"
    RESULTS_SCREEN = "RESULTS_SCREEN"


def current_state() -> CurrentState:
    img = ImageGrab.grab(text_locations["result_box"])
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    for text in data["text"]:
        if "Lvl" in text:
            return CurrentState.RESULTS_SCREEN

    img = ImageGrab.grab(text_locations["battle_box"])
    match = find_levels(img, LEVELS_TO_FIND)
    if match:
        return CurrentState.JOIN_SCREEN

    img = ImageGrab.grab(text_locations["like_box"])
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    for text in data["text"]:
        if text.isdigit():
            return CurrentState.HOME_SCREEN

    return CurrentState.BATTLE_SCREEN


text_locations = {}


def setup_text_locations():
    win = get_game_window()
    win.activate()
    text_locations["result_box"] = (
        win.left + 0.23 * win.width,
        win.top + 0.795 * win.height,
        win.right - 0.725 * win.width,
        win.bottom - 0.172 * win.height,
    )
    text_locations["back_button"] = (
        int(win.right - 0.5 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["join_button"] = (
        int(win.right - 0.15 * win.width),
        int(win.bottom - 0.18 * win.height),
    )
    text_locations["play_button"] = (
        int(win.right - 0.5 * win.width),
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
        win.left + 0.4 * win.width,
        win.top + 0.1 * win.height,
        win.right - 0.3 * win.width,
        win.bottom - 0.6 * win.height,
    )


def main():
    while True:
        pyautogui.sleep(1)
        state = current_state()
        print("Current State:", state)
        match state:
            case CurrentState.JOIN_SCREEN:
                start_join()
            case CurrentState.HOME_SCREEN:
                pydirectinput.click(
                    int(text_locations["join_screen_button"][0]),
                    int(text_locations["join_screen_button"][1]),
                )
            case CurrentState.BATTLE_SCREEN:
                pass
            case CurrentState.RESULTS_SCREEN:
                find_finish()


if __name__ == "__main__":
    setup_text_locations()
    main()
