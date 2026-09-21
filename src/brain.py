import os

from google import genai
from google.genai import types, errors

from actions import ActionPlan


PLANNER_SYSTEM = """
You are KAIRO's task planner.

Your job is to convert the user's request into a COMPLETE executable plan.

The plan has two parts:

1. GOALS
   These represent every meaningful outcome requested by the user.

2. ACTIONS
   These are the concrete keyboard, mouse, waiting, and application actions
   required to accomplish those goals.

RULES:

1. Extract EVERY user-requested outcome into `goals`.

2. NEVER omit a requested outcome.

3. NEVER invent a goal that the user did not request.

4. Every meaningful action must have a valid `goal_id`.

5. The final `done` action is allowed ONLY after every required goal has
   actions that can accomplish it.

6. Do not treat `done` as a goal.

7. Do not use trivial actions such as Win+D as a substitute for a requested
   meaningful action.

8. If the user says "save", the plan MUST actually perform the save operation.

   Normally this means:
   - open Save or Save As
   - provide the requested filename
   - confirm the save

9. If the user gives a specific filename, preserve it exactly.

10. If the user asks for a search, the plan must:
    - enter the requested search query
    - submit the search

11. If the user asks to open an application, the plan must actually launch it.

12. If the user asks for "something different", create a distinct,
    meaningful action that is clearly different from the preceding task.

13. Do not replace a specific requested action with a vague approximation.

14. Use waits where an application needs time to open.

15. Keep the plan executable using ONLY the available action types.

16. Do not stop early.

17. Do not add extra actions merely for the sake of making the plan longer.

18. Preserve the user's exact requested text, names, filenames, and search
    queries.

Before returning the plan, mentally check:

- Did I capture every requested goal?
- Does every goal have at least one corresponding action?
- Does every meaningful action have a goal_id?
- If there is a save goal, is there an actual save sequence?
- If there is a requested search, is the search actually submitted?
- If there is a requested additional/different action, is it actually present?
- Does the final done action occur only after all goals?
"""


REVISION_SYSTEM = """
You are KAIRO's plan repair system.

You are given:

1. The original user request.
2. An ActionPlan that failed KAIRO's local plan audit.
3. The exact reason why the plan failed.

Your job is to return a CORRECTED COMPLETE ActionPlan.

RULES:

1. Preserve the user's original intent.
2. Do not invent requirements that are not present in the user's request.
3. Do not remove valid goals.
4. Do not remove valid actions unless necessary to correct the plan.
5. Every meaningful action must reference a valid goal_id.
6. Every goal must have at least one action.
7. The final action MUST be `done`.
8. `done` must occur only at the end.
9. If the task includes saving a file, the corrected plan must contain the
   actual save sequence.
10. If the task contains a requested search, the corrected plan must actually
    perform the search.
11. If the user requested a distinct additional action, it must appear as its
    own goal and action sequence.
12. Preserve exact filenames, text, and search queries.
13. Do not create fake "verification" actions that do not actually accomplish
    the goal.
"""


class Brain:

    def __init__(self):

        raw_keys = os.getenv("GEMINI_API_KEYS")

        if not raw_keys:

            single_key = os.getenv("GEMINI_API_KEY")

            if not single_key:
                raise RuntimeError(
                    "GEMINI_API_KEYS or GEMINI_API_KEY is not set."
                )

            raw_keys = single_key

        self.api_keys = [
            key.strip()
            for key in raw_keys.split(";")
            if key.strip()
        ]

        if not self.api_keys:
            raise RuntimeError(
                "No Gemini API keys found."
            )

        self.clients = [
            genai.Client(api_key=key)
            for key in self.api_keys
        ]

        self.active_key = 0

        self.model = "gemini-3.5-flash-lite"

    # ---------------------------------------------------------
    # Gemini request helper
    # ---------------------------------------------------------

    def _generate_plan(self, prompt):

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ActionPlan,
            automatic_function_calling=(
                types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )

        for key_attempt in range(len(self.clients)):

            client = self.clients[self.active_key]

            print(
                f"[KAIRO] Using Gemini key "
                f"{self.active_key + 1}/{len(self.clients)}..."
            )

            try:

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return ActionPlan.model_validate_json(
                    response.text
                )

            except errors.APIError as e:

                if e.code == 429:

                    print(
                        f"[KAIRO] Key {self.active_key + 1} "
                        "hit a rate limit. Switching key..."
                    )

                    self.active_key = (
                        self.active_key + 1
                    ) % len(self.clients)

                    continue

                raise

        raise RuntimeError(
            "All configured Gemini keys/projects failed."
        )

    # ---------------------------------------------------------
    # Initial planning
    # ---------------------------------------------------------

    def plan(self, command):

        prompt = f"""
{PLANNER_SYSTEM}

USER REQUEST:
{command}

Return a complete ActionPlan.
"""

        print("[KAIRO] Generating initial plan...")

        plan = self._generate_plan(prompt)

        print("[KAIRO] Plan received.")

        return plan

    # ---------------------------------------------------------
    # Plan audit
    # ---------------------------------------------------------

    def audit_plan(self, command, plan):

        # -----------------------------------------------------
        # Check that goal IDs are unique.
        # -----------------------------------------------------

        goal_ids = [goal.id for goal in plan.goals]

        if len(goal_ids) != len(set(goal_ids)):

            raise ValueError(
                "Plan contains duplicate goal IDs."
            )

        goal_id_set = set(goal_ids)

        # -----------------------------------------------------
        # Check every action.
        # -----------------------------------------------------

        for action in plan.actions:

            # `done` is the only action that does not need a goal.
            if action.action == "done":
                continue

            if not action.goal_id:

                raise ValueError(
                    "A meaningful action is missing goal_id: "
                    f"{action.model_dump()}"
                )

            if action.goal_id not in goal_id_set:

                raise ValueError(
                    "Action references an unknown goal_id: "
                    f"{action.goal_id}"
                )

        # -----------------------------------------------------
        # Check that every goal is actually covered by actions.
        # -----------------------------------------------------

        covered_goals = {
            action.goal_id
            for action in plan.actions
            if action.action != "done"
        }

        missing_goals = (
            goal_id_set - covered_goals
        )

        if missing_goals:

            raise ValueError(
                "Plan contains goals with no actions: "
                f"{sorted(missing_goals)}"
            )

        # -----------------------------------------------------
        # `done` must exist and must be last.
        # -----------------------------------------------------

        done_positions = [
            index
            for index, action in enumerate(plan.actions)
            if action.action == "done"
        ]

        if not done_positions:

            raise ValueError(
                "Plan does not contain a final done action."
            )

        if done_positions[-1] != len(plan.actions) - 1:

            raise ValueError(
                "done must be the final action."
            )

        if len(done_positions) > 1:

            raise ValueError(
                "Plan contains multiple done actions."
            )

        # -----------------------------------------------------
        # Basic semantic checks for important actions.
        # -----------------------------------------------------

        for action in plan.actions:

            if action.action == "type":

                if action.text is None or action.text == "":

                    raise ValueError(
                        "A type action contains no text."
                    )

            elif action.action == "click_target":

                if not action.target:

                    raise ValueError(
                        "click_target action has no target."
                    )

            elif action.action == "wait":

                if action.seconds is None:

                    raise ValueError(
                        "wait action has no duration."
                    )

                if action.seconds < 0:

                    raise ValueError(
                        "wait action has a negative duration."
                    )

        print("[KAIRO] Plan audit passed.")

        return plan

    # ---------------------------------------------------------
    # Revise invalid plan
    # ---------------------------------------------------------

    def revise_plan(
        self,
        command,
        invalid_plan,
        reason
    ):

        print(
            "[KAIRO] Asking Gemini to revise "
            "the incomplete plan..."
        )

        invalid_plan_json = (
            invalid_plan.model_dump_json(
                indent=2
            )
        )

        prompt = f"""
{REVISION_SYSTEM}

ORIGINAL USER REQUEST:
{command}

INVALID ACTION PLAN:
{invalid_plan_json}

PLAN AUDIT FAILURE:
{reason}

Return a corrected COMPLETE ActionPlan.
"""

        revised_plan = self._generate_plan(
            prompt
        )

        print(
            "[KAIRO] Revised plan received."
        )

        return revised_plan