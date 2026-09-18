import os
import time

from google import genai
from google.genai import types, errors

from actions import ActionPlan


SYSTEM_PROMPT = """
You are the planning brain of KAIRO, a Windows computer-control agent.

Convert the user's request into a complete sequence of actions.

Available actions:

- hotkey
  {"action":"hotkey","keys":["win","r"]}

- press
  {"action":"press","key":"enter"}

- type
  {"action":"type","text":"hello world"}

- click_target
  {"action":"click_target","target":"Settings"}

- wait
  {"action":"wait","seconds":1}

- done
  {"action":"done"}

Rules:

- Return a complete plan.
- Do not return mouse coordinates.
- Use click_target whenever a GUI element needs to be located.
- Use keyboard actions when appropriate.
- Break complicated tasks into logical steps.
- Use wait when an application needs time to respond.
- Finish the plan with done.
- Do not use unnecessary actions.
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
            raise RuntimeError("No Gemini API keys found.")

        self.clients = [
            genai.Client(api_key=key)
            for key in self.api_keys
        ]

        self.active_key = 0

        self.model = "gemini-3.5-flash-lite"


    def plan(self, command):

        prompt = f"""
{SYSTEM_PROMPT}

USER REQUEST:
{command}

Create the complete action plan for this task.
"""

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

                print("[KAIRO] Plan received.")

                return ActionPlan.model_validate_json(
                    response.text
                )

            except errors.APIError as e:

                # 429 = quota/rate-limit exhaustion
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

            except Exception:
                raise

        raise RuntimeError(
            "All configured Gemini keys/projects failed."
        )