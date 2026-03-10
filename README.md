# Batch Simulate Protocols

This set of scripts helps simulate Opentrons protocols so they are ready for customer delivery. You can run a **single protocol** or a **folder of protocols**. Optionally, you can point to a folder of custom labware definitions. The workflow:

1. **Randomizes run-time parameters** — Generates many versions of each protocol by varying parameters (ints, floats, bools, choices) within their defined ranges.
2. **Runs simulations** — Simulates every generated protocol using `opentrons_simulate`.
3. **Reports failures** — Failed runs are captured; their parameters are written to a report for investigation. Full simulator output is saved for manual review.

---

## Quick start (recommended): launcher scripts

The easiest way to run the workflow is with the launcher scripts. They open dialogs to pick a protocol (or folder) and an optional labware folder, then run randomization and simulation for you. After the report is written, the launchers automatically clear **`generated_protocols/`** so you can run the workflow again without old variants piling up.

### macOS

1. Open the project folder in Finder.
2. Double-click **`batch_simulate.command`**.
3. In the dialog, choose **Single** (one `.py` protocol) or **Batch** (folder of protocols).
4. Select your protocol file or folder.
5. When prompted, select the folder containing your **labware definitions**, or click **Cancel** to skip.
6. The script runs in Terminal: randomization first, then mass simulation. When it finishes, check the report and outputs (see [Outputs](#outputs) below).

**Requirements:** Python 3 and `opentrons_simulate` on your `PATH`. The script uses `python3`.

### Windows

1. Open the project folder in File Explorer.
2. Right-click **`batch_simulate.ps1`** and choose **Run with PowerShell** (or run it from a PowerShell window).
3. In the dialog, choose **Single** or **Batch**.
4. Select your protocol file or folder.
5. When prompted, select your **labware** folder or cancel to skip.
6. The script runs: randomization, then mass simulation. Check the report and outputs when done.

**Requirements:** Python and `opentrons_simulate` on your `PATH`. The script uses `python`.

---

## Using the Python scripts from the command line

The launchers call two Python scripts that live in the **`Resources`** folder. You can run them yourself for more control (e.g. custom paths, non-interactive use).

**Project layout:**

- **`batch_simulate.command`** — macOS launcher (double-click).
- **`batch_simulate.ps1`** — Windows launcher (Run with PowerShell).
- **`Resources/`**
  - **`Randomized_RTP.py`** — Randomizes protocol parameters and writes generated protocols to `generated_protocols/`.
  - **`Mass_Simulation.py`** — Runs `opentrons_simulate` on protocols (default: `generated_protocols/`) and writes reports and raw outputs.

All output directories are created at the **project root** (the folder that contains `Resources/`), unless you override them with the options below.

### 1. Randomized_RTP.py

Generates protocol variants by varying parameters (min/default/max, choices, bools) and writes them into `generated_protocols/` (or a path you specify).

```bash
# From the project root (parent of Resources/)
python3 Resources/Randomized_RTP.py --file <path-to-protocol-or-folder> [options]
```

| Option | Short | Description |
|--------|--------|-------------|
| `--file` | `-f` | **Required.** Path to a single `.py` protocol or a folder of `.py` protocols. |
| `--output` | `-o` | Directory for generated protocol files. Default: `generated_protocols` at project root. |
| `--assume_yes` | `-y` | Assume “yes” for all prompts (e.g. overwrite confirmation). |

**Examples:**

```bash
# Single protocol, default output dir
python3 Resources/Randomized_RTP.py --file ./my_protocol.py --assume_yes

# Folder of protocols, custom output dir
python3 Resources/Randomized_RTP.py -f ./protocols_folder -o ./my_generated -y
```

### 2. Mass_Simulation.py

Simulates all protocols in a folder (default: `generated_protocols/`) with `opentrons_simulate`, writes raw outputs and a summary report.

```bash
python3 Resources/Mass_Simulation.py [options]
```

| Option | Short | Description |
|--------|--------|-------------|
| `--file` | `-f` | Folder of protocols to simulate. Default: `generated_protocols` at project root. |
| `--labware` | `-L` | Optional path to custom labware definitions. |
| `--output` | `-o` | Directory path for the simulation report file. Default: project root. |
| `--assume_yes` | `-y` | Assume “yes” for all prompts. |
| `--silent` | `-s` | Suppress most output; only the final report is shown. |
| `--cleanup-generated` | — | After writing the report, delete all files in the simulated protocols folder (e.g. `generated_protocols/`) so repeated runs don’t duplicate old variants. **Used by default when running via the launcher scripts.** |

**Examples:**

```bash
# Use default generated_protocols, with custom labware
python3 Resources/Mass_Simulation.py --labware ./my_labware --assume_yes

# Simulate a specific folder, silent run
python3 Resources/Mass_Simulation.py --file ./my_generated -s -y

# Keep generated_protocols after the run (default when not using the launcher)
python3 Resources/Mass_Simulation.py --file ./generated_protocols
# Clean them up after the report (same as launcher behavior)
python3 Resources/Mass_Simulation.py --cleanup-generated -s -y
```

### Full workflow from the command line

```bash
# 1. Generate protocol variants
python3 Resources/Randomized_RTP.py --file /path/to/protocols --assume_yes

# 2. Simulate them (optional: add --labware /path/to/labware; add --cleanup-generated to clear generated_protocols after the report, like the launchers)
python3 Resources/Mass_Simulation.py --silent --assume_yes --cleanup-generated
```

---

## Outputs

- **`generated_protocols/`** — Randomized protocol variants (created by `Randomized_RTP.py`).
- **`simulation_raw_outputs/`** — Per-protocol simulator stdout/stderr (for manual inspection).
- **`simulation_report.txt`** — Summary: total/success/fail counts and, for failures, the parameters used.

---

## Requirements

- Python 3
- [Opentrons Protocol API](https://docs.opentrons.com/) and **`opentrons_simulate`** on your `PATH`

Protocols must define an `add_parameters` function that uses the standard parameter API (`add_int`, `add_float`, `add_bool`, `add_str`, etc.) so the randomizer can discover ranges and choices.
