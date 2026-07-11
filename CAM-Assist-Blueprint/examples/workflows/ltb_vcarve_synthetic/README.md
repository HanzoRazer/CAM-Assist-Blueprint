# Synthetic V-Carve Workflow Example

This directory documents the canonical end-to-end CAM Assist demonstration. It
does **not** commit generated packages — the demonstration runner produces every
artifact in a temporary workspace so there is only one source of truth for the
example inputs.

## Input

The demonstration starts from the synthetic V-Carve LTB CAM output:

```text
examples/ltb_import/synthetic_vcarve_ltb_output.json
```

This is an explicitly synthetic manufacturing intent for a V-carve inlay
operation. It is imported into a CAM Assist strategy and carried all the way to a
reviewed, non-execution Production Shop handoff.

## Run it

Generate the full workflow into a temporary workspace (removed on exit):

```bash
python scripts/run_cam_assist_demo.py
```

Keep the artifacts for inspection:

```bash
python scripts/run_cam_assist_demo.py --workspace .tmp/cam_assist_demo --keep
```

Emit a machine-readable summary:

```bash
python scripts/run_cam_assist_demo.py --json
```

## What it produces

See [WORKFLOW_OUTPUTS.md](WORKFLOW_OUTPUTS.md) for the expected artifact set and the
step sequence.

## Non-execution

The demonstration generates no G-code, calls no CAM engine or machine, claims no
machine readiness, and never mutates the committed source examples. See
[docs/product/CAM_ASSIST_WORKFLOW.md](../../../docs/product/CAM_ASSIST_WORKFLOW.md)
for the same flow documented command by command.
