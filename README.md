# KAIRO

KAIRO is a local Windows desktop agent that accepts a natural-language task, uses Gemini for reasoning and planning, executes the resulting actions on Windows, and verifies important states before continuing or finishing.

The current architecture separates reasoning, execution, perception, and verification:

```text
User
  ↓
KAIRO GUI
  ↓
Gemini
  ↓
Structured ActionPlan
  ↓
Agent
  ├── Keyboard actions → Controller → Windows
  └── Visual actions  → Cursor Model → Controller → Windows
  ↓
Observer
  ↓
Local verification / Gemini verification
  ↺ targeted recovery when necessary
```

## Current architecture

### Gemini — reasoning and planning

Gemini is the high-level planner.

It receives the user's natural-language instruction and produces a structured `ActionPlan` made of:

- goals: what KAIRO must accomplish
- actions: how KAIRO should accomplish those goals
- expected state descriptions used by verification

KAIRO does not use a local LLM for planning.

### Agent — coordination

`src/agent.py` coordinates the complete execution loop.

It:

1. requests a plan from Gemini
2. executes actions in order
3. performs local Windows-side checks at important checkpoints
4. asks Gemini for targeted recovery when an intermediate state fails
5. records verified states
6. performs final goal verification
7. performs bounded final recovery when configured
8. stops rather than endlessly repeating failed work

### Controller — computer input

`src/controller.py` provides the low-level keyboard and mouse primitives used by KAIRO.

Current primitives include:

- move
- click
- type
- press
- hotkey
- wait

PyAutoGUI's fail-safe remains enabled.

### Observer — screen capture

`src/observer.py` captures the Windows screen when KAIRO needs visual state.

Screenshots are taken on demand rather than continuously.

### Cursor model

`src/cursor_model.py` is the interface for KAIRO's local visual cursor/target model.

The intended long-term pipeline is:

```text
Screenshot + target
        ↓
KAIRO Cursor Model
        ↓
predicted target position
        ↓
PyAutoGUI
```

The training dataset/configuration for the current TargetFinder work is under:

```text
data/targetfinder_yolo/
```

### Local verification

`src/local_verifier.py` performs inexpensive Windows-side checks where deterministic verification is possible.

Examples include:

- checking the active application window
- checking whether a saved file exists in configured locations
- checking file modification time for task-related saves

Local verification is preferred over spending a Gemini request when a fact can be checked deterministically.

### Gemini verification and recovery

`src/verifier.py` is used for semantic verification and targeted recovery.

The intended recovery behavior is:

```text
action fails
    ↓
local verification
    ↓
Gemini sees the current state
    ↓
small recovery plan
    ↓
resume the original task
```

The recovery system should repair the failed or missing part rather than blindly restarting the entire task.

## Repository structure

```text
project-cursor/
├── data/
│   └── targetfinder_yolo/
│       └── data.yaml
│
├── src/
│   ├── gui/
│   │   └── gui.qml
│   ├── actions.py
│   ├── agent.py
│   ├── brain.py
│   ├── bridge.py
│   ├── controller.py
│   ├── cursor_model.py
│   ├── executor.py
│   ├── local_verifier.py
│   ├── main.py
│   ├── observer.py
│   ├── planner.py
│   └── verifier.py
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Requirements

KAIRO is currently a **Windows-focused project** because the current controller, active-window verifier, and task examples rely on Windows behavior.

You will need:

- Windows
- Python
- a Gemini API key
- the Python packages listed in `requirements.txt`

The project was developed and tested with Python 3.14.6 during the current development cycle.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/KairosSyndicateOrg/project-cursor.git
cd project-cursor
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, you can use Command Prompt instead:

```bat
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Gemini API key

KAIRO uses Gemini for planning, verification, and recovery.

Set the API key before starting KAIRO.

### Option A — one API key

PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
```

Command Prompt:

```bat
set GEMINI_API_KEY=YOUR_API_KEY
```

### Option B — multiple keys

KAIRO's Gemini components support a comma-separated key list for key rotation.

PowerShell:

```powershell
$env:GEMINI_API_KEYS="KEY_1,KEY_2,KEY_3"
```

Do not commit API keys to GitHub.

For a permanent Windows environment variable, configure it in Windows rather than placing the key directly in Python source code.

## Start KAIRO

From the repository root:

```bash
python src/main.py
```

The GUI launches and connects to the Python agent through the Qt bridge.

Enter a task into the KAIRO command box and submit it.

Examples:

```text
Open Chrome
```

```text
Open Chrome and search for OpenAI
```

```text
Open Notepad, write a short note, and save it as test.txt
```

The exact result depends on the generated plan, the current Windows state, and the verification/recovery logic.

## How execution works

A normal task follows this sequence:

```text
1. User enters a task
        ↓
2. Gemini creates ActionPlan
        ↓
3. Agent validates the plan
        ↓
4. Executor performs actions
        ↓
5. Important states are locally verified
        ↓
6. Failed checkpoints can trigger targeted Gemini recovery
        ↓
7. Remaining original actions continue
        ↓
8. Final goal verification
        ↓
9. Success or bounded recovery
```

### Example action types

The current action model supports:

```json
{"action": "hotkey", "keys": ["win", "r"]}
```

```json
{"action": "press", "key": "enter"}
```

```json
{"action": "type", "text": "chrome"}
```

```json
{"action": "click_target", "target": "Settings"}
```

```json
{"action": "wait", "seconds": 1}
```

```json
{"action": "done"}
```

## Goals vs actions

KAIRO separates:

```text
Goal = WHAT needs to happen
Action = HOW to make it happen
```

For example:

```text
Goal:
Open Google Chrome

Actions:
Win + R
type "chrome"
press Enter
wait
```

This distinction allows the verifier to check whether the requested outcome was actually achieved instead of only checking whether keyboard commands were executed.

## Verification

KAIRO uses two levels of verification.

### Local verification

Used when Windows can answer the question deterministically.

Examples:

```text
"Is Chrome the active application?"
"Does the saved file exist?"
"Was the file modified during this task?"
```

### Gemini verification

Used for semantic or visual states that are harder to determine locally.

Examples:

```text
"Did the requested search actually happen?"
"Was the requested content entered correctly?"
"Did the task's final goals get completed?"
```

The system is intentionally designed so that deterministic checks happen locally before asking Gemini.

## TargetFinder dataset

The current dataset configuration is:

```text
data/targetfinder_yolo/data.yaml
```

Classes:

```text
0: Button
1: ToggleButton
2: TextInput
3: Slider
4: Text
5: Hyperlink
```

The actual screenshot/label dataset is intentionally not required to live inside the Git repository.

If you are training the cursor model, obtain the dataset separately and place it in:

```text
data/targetfinder_yolo/
├── data.yaml
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

`data.yaml` should use a repository-relative path:

```yaml
path: data/targetfinder_yolo

train: images/train
val: images/val

names:
  0: Button
  1: ToggleButton
  2: TextInput
  3: Slider
  4: Text
  5: Hyperlink
```

## Running the cursor-model experiments

The repository contains the interface for the cursor model, but the training workflow may evolve as the model architecture is developed.

The intended final interface is:

```text
screenshot + target
        ↓
cursor model
        ↓
target coordinates
        ↓
controller
```

Training artifacts, experiment outputs, large datasets, and model weights should generally stay out of normal Git commits unless the project explicitly decides to version them.

## Safety

KAIRO controls a real Windows desktop.

Keep PyAutoGUI's fail-safe enabled.

Before testing autonomous actions:

- save important work
- close applications you do not want KAIRO to interact with
- test new plans with harmless tasks
- do not run untrusted action plans blindly
- inspect the generated plan when debugging

The project is under active development, so task execution should not be treated as guaranteed or fully autonomous.

## Development

The repository is structured so individual components can be developed separately:

```text
Planner
  ↓
Agent
  ↓
Executor
  ↓
Controller
  ↓
Windows
  ↓
Observer
  ↓
Verifier
```

When changing one component, try to preserve the interfaces used by the other components.

### Useful development commands

Run KAIRO:

```bash
python src/main.py
```

Run an individual module while debugging:

```bash
python src/agent.py
```

Check Git status:

```bash
git status
```

## Contributing

KAIRO is being developed as a student-built open-source project.

Before submitting a change:

1. keep the change focused
2. test it locally on Windows
3. avoid committing API keys, datasets, screenshots, model weights, or generated artifacts unless explicitly intended
4. update the README when setup or architecture changes
5. use a clear commit message

Example:

```text
feat: add visual target detection
```

```text
fix: make dataset path portable
```

```text
refactor: simplify recovery flow
```

## Current limitations

KAIRO is still experimental.

Important current limitations include:

- Windows is the primary supported environment.
- GUI interaction through the local cursor model is still under development.
- Visual verification is not perfect.
- Some state checks are intentionally reported as uncertain rather than guessed.
- Save verification currently relies on configured/common locations rather than an arbitrary filesystem location.
- Gemini-generated plans can still make planning mistakes, so recovery and verification remain important.
- The cursor model is not yet the final production-quality vision system.

## License

This project is distributed under the MIT License.

See [`LICENSE`](LICENSE).

## Project status

KAIRO is under active development.

The long-term goal is to build a system that can understand a user's task, reason about the required steps, operate a graphical interface, observe the resulting state, and recover from failures without relying on brittle fixed scripts.
