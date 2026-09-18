from brain import Brain
from executor import Executor
from observer import ScreenObserver


class Agent:

    def __init__(self, cursor_model=None):

        self.brain = Brain()

        self.executor = Executor(
            cursor_model=cursor_model
        )

        self.observer = ScreenObserver()

    def run(self, command):

        print("\n[KAIRO] Starting task:")
        print(command)

        # --------------------------------
        # 1. Ask Gemini for the plan ONCE
        # --------------------------------

        plan = self.brain.plan(command)

        print("\n[KAIRO] Plan:")

        for index, action in enumerate(
            plan.actions,
            start=1
        ):
            print(
                f"{index}. "
                f"{action.model_dump()}"
            )

        # --------------------------------
        # 2. Execute locally
        # --------------------------------

        for action in plan.actions:

            print(
                f"\n[KAIRO] Executing: "
                f"{action.model_dump()}"
            )

            # Get current screen.
            observation = self.observer.observe()

            screenshot = observation["image"]

            # Execute action.
            result = self.executor.execute(
                action,
                screenshot=screenshot
            )

            # Stop at done.
            if result == "DONE":

                print(
                    "\n[KAIRO] Task completed."
                )

                break


if __name__ == "__main__":

    agent = Agent()

    agent.run(
        " open chrome,search for mr beast ."
    )