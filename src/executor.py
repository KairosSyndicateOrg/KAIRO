from controller import move, click, type_text, press, hotkey, wait


class Executor:
    def __init__(self, cursor_model=None):
        self.cursor_model = cursor_model

    def execute(self, action, screenshot=None):

        if action.action == "hotkey":
            hotkey(*action.keys)

        elif action.action == "press":
            press(action.key)

        elif action.action == "type":
            type_text(action.text)

        elif action.action == "wait":
            wait(action.seconds)

        elif action.action == "click_target":
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

            x, y = result["center"]

            move(x, y)
            click(x, y)

        elif action.action == "done":
            return "DONE"

        else:
            raise ValueError(
                f"Unknown action: {action.action}"
            )

        return "OK"