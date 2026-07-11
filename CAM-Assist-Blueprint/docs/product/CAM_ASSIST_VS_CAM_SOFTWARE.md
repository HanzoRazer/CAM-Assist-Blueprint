# CAM Assist vs Traditional CAM

CAM Assist is not a replacement for traditional CAM software. They occupy
different stages of the manufacturing story and are best understood as
complementary.

## Capability comparison

| Capability            | CAM Assist |         Traditional CAM |
| --------------------- | ---------: | ----------------------: |
| Manufacturing intent  |        Yes |               Sometimes |
| Human review package  |        Yes |                 Limited |
| Assumptions and risks |        Yes |        Usually external |
| Revision lineage      |        Yes |         Vendor-specific |
| Traceability bundle   |        Yes |        Usually external |
| Toolpath generation   |         No |                     Yes |
| Simulation            |         No |                     Yes |
| G-code generation     |         No |                     Yes |
| Post-processing       |         No |                     Yes |
| Machine execution     |         No | No/Controller-dependent |

## How to read this table

- **CAM Assist owns the reasoning layer**: intent, review, assumptions, risk,
  rationale, lineage, and portable traceability. These are captured explicitly
  and travel with the package.
- **Traditional CAM owns the execution layer**: toolpath generation, simulation,
  G-code, and post-processing. CAM Assist deliberately does **none** of these — it
  generates no G-code and grants no execution authority.

## A note on traceability

Traditional CAM does not *never* support traceability. Rather, such support is
**often vendor-specific or external to the CAM project** — captured in a separate
PLM/quality system, a vendor's proprietary format, or an operator's notes. CAM
Assist's contribution is to make that reasoning a **portable, reviewable,
first-class artifact** that is not locked to a single tool or vendor.

## The dividing line

```text
Traditional CAM:
CAD → CAM → Toolpath → Post → Machine

CAM Assist:
Design Intent → Manufacturing Strategy → Review → Portable Package
                                                   ↓
                                             Downstream CAM
```

Traditional CAM begins roughly where CAM Assist ends. CAM Assist stays upstream of
execution; it never claims a package is machine-ready.
