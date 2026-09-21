import os

from google import genai
from google.genai import types, errors
from pydantic import BaseModel, Field

from actions import Action


# ---------------------------------------------------------
# Recovery plan
# ---------------------------------------------------------

class RecoveryPlan(BaseModel):
    actions: list[Action] = Field(min_length=1)


# ---------------------------------------------------------
# Intermediate verification result
# ---------------------------------------------------------

class VerificationResult(BaseModel):
    success: bool
    reason: str
    recovery_plan: RecoveryPlan | None = None


# ---------------------------------------------------------
# Final verification result
# ---------------------------------------------------------

class FinalVerificationResult(BaseModel):
    success: bool
    reason: str


class Verifier:

    def __init__(self):

        raw_keys = os.getenv(
            "GEMINI_API_KEYS"
        )

        if not raw_keys:

            single_key = os.getenv(
                "GEMINI_API_KEY"
            )

            if not single_key:

                raise RuntimeError(
                    "GEMINI_API_KEYS or "
                    "GEMINI_API_KEY is not configured."
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

        self.model = "gemini-3.5-flash-lite"

        self.index = 0

    # ---------------------------------------------------------
    # Gemini request helper
    # ---------------------------------------------------------

    def _generate(
        self,
        contents,
        response_schema
    ):

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            automatic_function_calling=(
                types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )

        for _ in range(len(self.clients)):

            client_index = self.index

            client = self.clients[
                client_index
            ]

            print(
                f"[KAIRO] Verifier using Gemini key "
                f"{client_index + 1}/"
                f"{len(self.clients)}..."
            )

            self.index = (
                self.index + 1
            ) % len(self.clients)

            try:

                response = (
                    client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=config,
                    )
                )

                if not response.text:

                    raise RuntimeError(
                        "Gemini returned an empty "
                        "verification response."
                    )

                return response

            except errors.APIError as e:

                if e.code == 429:

                    print(
                        f"[KAIRO] Verifier key "
                        f"{client_index + 1} "
                        "hit a rate limit. "
                        "Switching key..."
                    )

                    continue

                raise

        raise RuntimeError(
            "All configured Gemini keys/projects "
            "failed during verification."
        )

    # ---------------------------------------------------------
    # Intermediate step recovery
    # ---------------------------------------------------------

    def recover_step(
        self,
        command,
        failed_action,
        current_image,
        local_result,
        verified_states=None,
        remaining_actions=None
    ):

        expected = failed_action.expected

        if expected is None:

            expected = (
                "No explicit expected state was provided. "
                "Recover only what is directly implied "
                "by the failed action and original goal."
            )

        verified_states_text = "\n".join(
            f"- {state}"
            for state in (verified_states or [])
        )

        if not verified_states_text:

            verified_states_text = "None."

        remaining_actions_text = "\n".join(
            f"- {action}"
            for action in (remaining_actions or [])
        )

        if not remaining_actions_text:

            remaining_actions_text = "None."

        prompt = f"""
You are KAIRO's intermediate step-recovery system.

ORIGINAL USER GOAL:
{command}

VERIFIED STATES ALREADY ACHIEVED:
{verified_states_text}

REMAINING ORIGINAL ACTIONS:
{remaining_actions_text}

FAILED ACTION:
{failed_action.model_dump_json()}

EXPECTED STATE:
{expected}

DETERMINISTIC LOCAL VERIFICATION RESULT:
{local_result}

Your job is ONLY to repair the failed action.

CRITICAL RULES:

- The ORIGINAL USER GOAL is the only source of truth.
- Do not invent new user requirements.
- Do not add unrelated tasks.
- Do not restart the entire task.
- Do not undo states that have already been verified.
- Do not repeat actions that are already verified.
- Preserve all successfully completed work.
- Repair ONLY the failed action.
- After repairing it, the Agent will continue
  the remaining original actions.
- Create the smallest possible recovery plan.
- Do not return mouse coordinates.
- Only use:
    hotkey
    press
    type
    click_target
    wait
    done
- Never invent unsupported keyboard keys.
- Every non-done recovery action must contain
  an accurate expected field.
- Do not claim that an application is active if
  the deterministic local verifier says otherwise.
- The local verifier's active-window information
  is authoritative when provided.
- If the expected state is already present,
  return success=true and recovery_plan=null.
- Do NOT create a recovery plan containing the
  remaining original task actions.
- Do NOT add save/download/write/search actions
  unless those are required to repair the failed action.

Return JSON matching the recovery schema.
"""

        response = self._generate(
            [
                prompt,
                "CURRENT SCREENSHOT:",
                current_image,
            ],
            response_schema=VerificationResult
        )

        return VerificationResult.model_validate_json(
            response.text
        )

    # ---------------------------------------------------------
    # Final goal verification
    # ---------------------------------------------------------

    def verify_goal(
        self,
        command,
        final_image,
        verified_states=None
    ):

        verified_states_text = "\n".join(
            f"- {state}"
            for state in (verified_states or [])
        )

        if not verified_states_text:

            verified_states_text = "None."

        prompt = f"""
You are KAIRO's final goal-verification system.

ORIGINAL USER GOAL:
{command}

VERIFIED STATES ALREADY ACHIEVED:
{verified_states_text}

The screenshot shows the final computer state.

Determine ONLY whether the ORIGINAL USER GOAL
has been achieved.

RULES:

- The ORIGINAL USER GOAL is the only source of truth.
- Do not invent new requirements.
- Do not infer unrelated tasks from visible text.
- Do not add actions that the user never requested.
- Preserve everything that has already been successfully completed.
- success=true ONLY when there is enough evidence
  that the ORIGINAL USER GOAL has been completed.
- If the evidence is ambiguous, return success=false.
- Do not assume an action happened merely because
  the planner intended to perform it.
- Distinguish between "planned" and "actually achieved".
- If a file was supposed to be saved, require evidence
  that the save actually occurred.
- If the user requested a specific action, require
  evidence that the requested action actually occurred.
- Do not use Win+D or similar actions as evidence of
  completing an unspecified task.
- Do not invent a "different action".
- Do not create requirements that were not in the
  original request.

Return JSON matching the final verification schema.
"""

        response = self._generate(
            [
                prompt,
                "FINAL SCREENSHOT:",
                final_image,
            ],
            response_schema=FinalVerificationResult
        )

        return FinalVerificationResult.model_validate_json(
            response.text
        )