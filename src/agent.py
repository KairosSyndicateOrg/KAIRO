import time

from brain import Brain
from executor import Executor
from observer import ScreenObserver
from verifier import Verifier
from local_verifier import LocalVerifier


class Agent:

    MAX_REPAIR_DEPTH = 3

    def __init__(self, cursor_model=None):

        self.brain = Brain()

        self.executor = Executor(
            cursor_model=cursor_model
        )

        self.observer = ScreenObserver()

        # Gemini is used for:
        # 1. Repairing failed intermediate states
        # 2. Final goal verification
        self.verifier = Verifier()

        # Cheap deterministic Windows-side verification.
        self.local_verifier = LocalVerifier()

        # States that KAIRO has already confirmed.
        self.verified_states = []

        # Used for filesystem verification so we can
        # distinguish a file created during this task
        # from an unrelated old file.
        self.task_started_at = None

    def execute_plan(
        self,
        plan,
        command,
        start_index=0,
        repair_depth=0
    ):
        """
        Execute a plan starting at start_index.

        If an action fails:
        1. Ask Gemini to repair ONLY that failed action.
        2. Execute the repair plan.
        3. Resume the original plan AFTER the failed action.
        """

        last_typed = None

        for index in range(
            start_index,
            len(plan.actions)
        ):

            action = plan.actions[index]

            print(
                f"\n[KAIRO] Action {index + 1}: "
                f"{action.model_dump()}"
            )

            # --------------------------------
            # DONE
            # --------------------------------

            if action.action == "done":

                print(
                    "[KAIRO] Plan reached done."
                )

                return True

            # --------------------------------
            # Screenshot only when the
            # executor actually needs one.
            # --------------------------------

            screenshot = None

            if action.action == "click_target":

                screenshot = (
                    self.observer.observe()["image"]
                )

            # --------------------------------
            # Execute action
            # --------------------------------

            try:

                result = self.executor.execute(
                    action,
                    screenshot=screenshot
                )

            except Exception as e:

                print(
                    f"[KAIRO ERROR] Executor failed: {e}"
                )

                return False

            print(
                f"[KAIRO] Executor result: {result}"
            )

            # --------------------------------
            # Remember what was typed.
            #
            # We intentionally keep the last
            # typed value through an Enter press,
            # because this lets us identify things
            # such as:
            #
            # type("kkl")
            # press("enter")
            #
            # as a save checkpoint.
            # --------------------------------

            if action.action == "type":

                last_typed = action.text

            elif not (
                action.action == "press"
                and action.key
                and action.key.lower() == "enter"
            ):

                last_typed = None

            # --------------------------------
            # DETERMINISTIC FILE-SAVE CHECK
            # --------------------------------

            if self.local_verifier.is_save_checkpoint(
                action=action,
                last_typed=last_typed
            ):

                print(
                    "\n[KAIRO] File-save verification checkpoint..."
                )

                local_result = (
                    self.local_verifier.check_saved_file(
                        filename=last_typed,
                        started_at=self.task_started_at
                    )
                )

                print(
                    "[KAIRO] File verification:"
                )

                print(local_result)

                # --------------------------------
                # File save succeeded.
                # --------------------------------

                if local_result["status"] == "SUCCESS":

                    print(
                        "[KAIRO] File save verified."
                    )

                    state = local_result["reason"]

                    if state not in self.verified_states:

                        self.verified_states.append(
                            state
                        )

                    continue

                # --------------------------------
                # File save definitely failed.
                # --------------------------------

                if local_result["status"] == "FAILED":

                    print(
                        "[KAIRO] File save verification failed."
                    )

                    if repair_depth >= self.MAX_REPAIR_DEPTH:

                        print(
                            "[KAIRO] Maximum repair depth reached."
                        )

                        return False

                    current_image = (
                        self.observer.observe()["image"]
                    )

                    remaining_actions = [
                        a.model_dump()
                        for a in plan.actions[index + 1:]
                    ]

                    print(
                        "[KAIRO] Asking Gemini for "
                        "save-step recovery..."
                    )

                    recovery = self.verifier.recover_step(
                        command=command,
                        failed_action=action,
                        current_image=current_image,
                        local_result=local_result,
                        verified_states=self.verified_states,
                        remaining_actions=remaining_actions
                    )

                    print(
                        "[KAIRO] Gemini recovery decision:"
                    )

                    print(
                        recovery.model_dump()
                    )

                    if recovery.success:

                        print(
                            "[KAIRO] Expected save state "
                            "is already present."
                        )

                        return self.execute_plan(
                            plan=plan,
                            command=command,
                            start_index=index + 1,
                            repair_depth=repair_depth
                        )

                    if recovery.recovery_plan is None:

                        print(
                            "[KAIRO] No recovery plan available."
                        )

                        return False

                    print(
                        "[KAIRO] Executing save repair plan..."
                    )

                    repair_success = self.execute_plan(
                        plan=recovery.recovery_plan,
                        command=command,
                        start_index=0,
                        repair_depth=repair_depth + 1
                    )

                    if not repair_success:

                        print(
                            "[KAIRO] Save repair plan failed."
                        )

                        return False

                    print(
                        "[KAIRO] Save repair succeeded."
                    )

                    print(
                        "[KAIRO] Resuming original plan "
                        f"from action {index + 2}."
                    )

                    return self.execute_plan(
                        plan=plan,
                        command=command,
                        start_index=index + 1,
                        repair_depth=repair_depth
                    )

                # --------------------------------
                # Filesystem check couldn't decide.
                # --------------------------------

                print(
                    "[KAIRO] File-save verification "
                    "was uncertain."
                )

                continue

            # --------------------------------
            # LOCAL CHECKPOINT
            # --------------------------------

            if not self.local_verifier.should_check(
                action,
                last_typed
            ):
                continue

            print(
                "\n[KAIRO] Local verification checkpoint..."
            )

            local_result = (
                self.local_verifier.check_active_app(
                    expected=action.expected,
                    last_typed=last_typed
                )
            )

            print(
                "[KAIRO] Local verification:"
            )

            print(local_result)

            # --------------------------------
            # Local verification succeeded.
            # --------------------------------

            if local_result["status"] == "SUCCESS":

                print(
                    "[KAIRO] Local check passed."
                )

                state = local_result["reason"]

                if state not in self.verified_states:

                    self.verified_states.append(
                        state
                    )

                continue

            # --------------------------------
            # Local verification failed.
            # --------------------------------

            if local_result["status"] == "FAILED":

                print(
                    "[KAIRO] Local check failed."
                )

                if repair_depth >= self.MAX_REPAIR_DEPTH:

                    print(
                        "[KAIRO] Maximum repair depth reached."
                    )

                    return False

                current_image = (
                    self.observer.observe()["image"]
                )

                remaining_actions = [
                    a.model_dump()
                    for a in plan.actions[index + 1:]
                ]

                print(
                    "[KAIRO] Asking Gemini for "
                    "step recovery..."
                )

                recovery = self.verifier.recover_step(
                    command=command,
                    failed_action=action,
                    current_image=current_image,
                    local_result=local_result,
                    verified_states=self.verified_states,
                    remaining_actions=remaining_actions
                )

                print(
                    "[KAIRO] Gemini recovery decision:"
                )

                print(
                    recovery.model_dump()
                )

                # Gemini says the expected state is
                # already satisfied.
                if recovery.success:

                    print(
                        "[KAIRO] Expected state is "
                        "already present."
                    )

                    return self.execute_plan(
                        plan=plan,
                        command=command,
                        start_index=index + 1,
                        repair_depth=repair_depth
                    )

                if recovery.recovery_plan is None:

                    print(
                        "[KAIRO] No recovery plan available."
                    )

                    return False

                print(
                    "[KAIRO] Executing repair plan..."
                )

                repair_success = self.execute_plan(
                    plan=recovery.recovery_plan,
                    command=command,
                    start_index=0,
                    repair_depth=repair_depth + 1
                )

                if not repair_success:

                    print(
                        "[KAIRO] Repair plan failed."
                    )

                    return False

                print(
                    "[KAIRO] Repair succeeded."
                )

                print(
                    "[KAIRO] Resuming original plan "
                    f"from action {index + 2}."
                )

                return self.execute_plan(
                    plan=plan,
                    command=command,
                    start_index=index + 1,
                    repair_depth=repair_depth
                )

            # --------------------------------
            # Local verification uncertain.
            # --------------------------------

            print(
                "[KAIRO] Local verifier is uncertain."
            )

        return True

    def run(self, command):

        print("\n[KAIRO] Starting task:")
        print(command)

        # Reset state from any previous task.
        self.verified_states.clear()

        # Mark the beginning of the task.
        self.task_started_at = time.time()

        # --------------------------------
        # Initial planning
        # --------------------------------

        plan = self.brain.plan(command)

        # --------------------------------
        # Audit plan BEFORE execution
        # --------------------------------

        try:

            plan = self.brain.audit_plan(
                command=command,
                plan=plan
            )

        except ValueError as e:

            print(
                "\n[KAIRO] Initial plan audit failed:"
            )

            print(
                f"[KAIRO] {e}"
            )

            print(
                "[KAIRO] Asking Gemini to "
                "repair the complete plan..."
            )

            plan = self.brain.revise_plan(
                command=command,
                invalid_plan=plan,
                reason=str(e)
            )

            # Revised plan MUST pass audit.
            plan = self.brain.audit_plan(
                command=command,
                plan=plan
            )

        # --------------------------------
        # Display goals
        # --------------------------------

        print("\n[KAIRO] Goals:")

        for goal in plan.goals:

            print(
                f"- [{goal.id}] "
                f"{goal.description}"
            )

        # --------------------------------
        # Display actions
        # --------------------------------

        print("\n[KAIRO] Initial plan:")

        for index, action in enumerate(
            plan.actions,
            start=1
        ):

            print(
                f"{index}. "
                f"{action.model_dump()}"
            )

        # --------------------------------
        # Execute
        # --------------------------------

        completed = self.execute_plan(
            plan=plan,
            command=command
        )

        if not completed:

            print(
                "\n[KAIRO] Current plan could not "
                "be completed."
            )

            return False

        # --------------------------------
        # Final goal verification
        # --------------------------------

        print(
            "\n[KAIRO] Final goal verification..."
        )

        final_image = (
            self.observer.observe()["image"]
        )

        verification = self.verifier.verify_goal(
            command=command,
            final_image=final_image,
            verified_states=self.verified_states
        )

        print(
            "[KAIRO] Final verification:"
        )

        print(
            verification.model_dump()
        )

        if verification.success:

            print(
                "\n[KAIRO] Task completed successfully."
            )

            return True

        print(
            "\n[KAIRO] Final goal verification failed."
        )

        print(
            f"[KAIRO] Reason: {verification.reason}"
        )

        print(
            "[KAIRO] Stopping instead of restarting "
            "already-completed work."
        )

        return False


if __name__ == "__main__":

    agent = Agent()

    success = agent.run(
        "open chrome and open notepad"
    )

    print(
        f"\n[KAIRO] Final result: {success}"
    )