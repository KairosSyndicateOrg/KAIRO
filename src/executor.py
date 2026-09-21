from controller import (
    move,
    click,
    type_text,
    press,
    hotkey,
    wait,
)


class Executor:

    def __init__(self, cursor_model=None):
        self.cursor_model = cursor_model

    def execute(self, action, screenshot=None):

        # --------------------------------
        # Keyboard shortcut
        # --------------------------------

        if action.action == "hotkey":

            if not action.keys:
                raise RuntimeError(
                    "hotkey action requires at least one key."
                )

            hotkey(*action.keys)

        # --------------------------------
        # Single key press
        # --------------------------------

        elif action.action == "press":

            if not action.key:
                raise RuntimeError(
                    "press action requires a key."
                )

            press(action.key)

        # --------------------------------
        # Type text
        # --------------------------------

        elif action.action == "type":

            if action.text is None:
                raise RuntimeError(
                    "type action requires text."
                )

            type_text(action.text)

        # --------------------------------
        # Wait
        # --------------------------------

        elif action.action == "wait":

            if action.seconds is None:
                raise RuntimeError(
                    "wait action requires seconds."
                )

            if action.seconds < 0:
                raise RuntimeError(
                    "wait action cannot use negative seconds."
                )

            wait(action.seconds)

        # --------------------------------
        # Click a visually identified target
        # --------------------------------

        elif action.action == "click_target":

            if not action.target:
                raise RuntimeError(
                    "click_target requires a target."
                )

            if self.cursor_model is None:
                raise RuntimeError(
                    "click_target requires the local cursor model."
                )

            if screenshot is None:
                raise RuntimeError(
                    "click_target requires a current screenshot."
                )

            result = self.cursor_model.find_target(
                screenshot,
                action.target
            )

            if not result:
                raise RuntimeError(
                    f"Cursor model could not find "
                    f"target: {action.target}"
                )

            if "center" not in result:
                raise RuntimeError(
                    "Cursor model result does not contain "
                    "'center'."
                )

            x, y = result["center"]

            move(x, y)
            click(x, y)

        # --------------------------------
        # End of plan
        # --------------------------------

        elif action.action == "done":

            return "DONE"

        # --------------------------------
        # Unknown action
        # --------------------------------

        else:

            raise ValueError(
                f"Unknown action: {action.action}"
            )

        return "OK"