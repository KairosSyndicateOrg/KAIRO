import time

import pyautogui


def move(
    x,
    y,
    duration=0.45
):

    pyautogui.moveTo(
        x,
        y,
        duration=duration,
        tween=pyautogui.easeInOutQuad
    )


def click(
    x,
    y
):

    pyautogui.click(
        x,
        y
    )


def type_text(
    text
):

    if text is None:
        raise ValueError(
            "type_text requires text."
        )

    pyautogui.write(
        text,
        interval=0.02
    )


def press(
    key
):

    if not key:
        raise ValueError(
            "press requires a key."
        )

    pyautogui.press(
        key
    )


def hotkey(
    *keys
):

    if not keys:
        raise ValueError(
            "hotkey requires at least one key."
        )

    pyautogui.hotkey(
        *keys
    )


def wait(
    seconds=0.5
):

    if seconds < 0:
        raise ValueError(
            "wait cannot use negative seconds."
        )

    time.sleep(
        seconds
    )