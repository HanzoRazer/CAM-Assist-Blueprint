# Pickup Route Strategy Review Packet

**Strategy ID:** `pickup-route-flat-sample`
**Generated:** 2026-08-30T05:18:15.290157

---

## 1. Non-Execution Notice


> **NON-EXECUTION NOTICE**
>
> This review packet is advisory only.
> It does not authorize machine execution.
> It does not generate G-code.
> It does not replace operator judgment.
> Human review and downstream CAM verification are required before machining.


---

## 2. Strategy Identity

| Field | Value |
|-------|-------|
| Strategy ID | `pickup-route-flat-sample` |
| Strategy Version | 1.2 |
| Approval State | pending |
| Source Spec ID | sample-body-pickup-route |
| CAM Assist Version | 0.5.0 |
| Created At | 2026-08-30T00:00:00Z |
| Created By | cam-assist-blueprint |

---

## 3. Instrument Context

**Source Specification:** `sample-body-pickup-route`

---

## 4. Material Context

| Property | Value |
|----------|-------|
| Material Class | hardwood |
| Species | Alder |
| Janka Hardness | 590 |
| Grain Direction | along_body_length |

---

## 5. Operation Intent

| Property | Value |
|----------|-------|
| Operation Type | pickup_route |
| Target Feature | body |
| Cut Intent | pocket |
| Geometry Type | 2.5D |
| Strategy Complexity | compound |
| Non-Execution Declaration | **True** |

---

## 6. Coordinate Frame

| Axis | Definition |
|------|------------|
| Origin | body_center |
| X-Axis | along_body_toward_bridge |
| Y-Axis | across_body_treble_positive |
| Z-Axis | into_body_blank |
| Datum Point | (0, 0, 0) |

**Units:** inches

---

## 7. Pickup Route Summary

### Overview

| Property | Value |
|----------|-------|
| Operation Type | pickup_route |
| Geometry Type | 2.5D |
| Strategy Complexity | compound |
| Cut Intent | pocket |
| Cavity Center | (0, 0) |
| Cavity Length | 3 inches |
| Cavity Width | 1.5 inches |
| Corner Radius | 0.125 inches |
| Final Depth | 0.75 inches |
| Bottom Profile | flat |
| Finish Allowance | 0.02 inches |
| Mounting Tabs | 1 |

*`geometry.dxf_file` is `geometry.dxf` as a contract filename. This package does not generate or include a DXF file.*

### Mounting Tabs

| # | Center X | Center Y | Length | Width | Corner Radius |
|---|----------|----------|--------|-------|---------------|
| 1 | 1.5 | 0 | 0.5 inches | 0.375 inches | 0.0625 inches |

### Roughing Depth Strategy

| Property | Value |
|----------|-------|
| Final Depth | 0.75 inches |
| Maximum Pass Depth | 0.25 inches |
| Pass Count | 3 |
| Passes | 0.25, 0.5, 0.75 |

*Depth passes are a manufacturing-strategy sequence. They are not G-code or cutter-center motion.*

### Finishing Depth Strategy

| Property | Value |
|----------|-------|
| Final Depth | 0.75 inches |

*Finishing expresses completion at the already-established target depth. It does not repeat the roughing pass list.*

### Tool Compatibility

| Property | Value |
|----------|-------|
| Status | compatible |
| Recommendation | recommended |
| Roughing Diameter | 0.25 inches |
| Roughing Claims Final Walls | False |
| Finishing Diameter | 0.25 inches |
| Finishing Tool Radius | 0.125 inches |
| Finishing Claims Final Walls | True |
| Tool-Limited Sharp | False |

---

## 8. Tool Assumptions

| Property | Value |
|----------|-------|
| Tool Type | end_mill |
| Reference Type | dimension_spec |
| Diameter | 0.25 inches |
| Description | End mill for cavity finishing |

| Compatibility | Value |
|---------------|-------|
| Status | compatible |
| Recommendation | recommended |
| Roughing Diameter | 0.25 inches |
| Roughing Claims Final Walls | False |
| Finishing Diameter | 0.25 inches |
| Finishing Claims Final Walls | True |
| Tool-Limited Sharp | False |

*Tool fit is geometric compatibility only. It is not execution approval.*

---

## 9. Workholding Assumptions

Body blank must be secured against movement during cavity routing. This is an advisory manufacturing assumption, not a fixture program or work-offset assignment.

> **Operator Note:** Verify adequate workholding before machining.
> Body blank must be secured against movement during cavity routing.

*Workholding notes are advisory manufacturing assumptions. They are not fixture programs or work-offset assignments.*

---

## 10. Safety Boundary

| Property | Value |
|----------|-------|
| Non-Execution Declaration | **True** |
| Human Review Required | **True** |
| Max Depth | 0.75 inches |
| Tool Diameter | 0.25 inches |
| Execution Authority Claim | **False** |

---

## 11. Human Review Requirements

Before proceeding to CAM or machining, the operator must verify:

- [ ] Cavity center, length, and width match the intended pickup location.
- [ ] Corner radius matches the intended cavity corners, including tool-limited-sharp when radius is 0.
- [ ] Final depth matches the intended cavity and does not overcut the blank.
- [ ] Mounting tabs, when present, contact the main cavity envelope.
- [ ] Roughing and finishing cutters both fit the cavity envelope.
- [ ] Cutters that claim final wall geometry satisfy a positive corner-radius constraint.
- [ ] Finish allowance is wall stock only and is understood by the operator.
- [ ] Depth-pass sequence reaches final depth without overcutting.
- [ ] This package is advisory only and does not authorize machine execution.

### Review Evidence

| Item | Value |
|------|-------|
| cavity_length | 3 inches |
| cavity_width | 1.5 inches |
| corner_radius | 0.125 inches |
| final_depth | 0.75 inches |
| roughing_tool_diameter | 0.25 inches |
| finishing_tool_diameter | 0.25 inches |
| finishing_tool_radius | 0.125 inches |
| finish_allowance | 0.02 inches |
| roughing_claims_final_walls | False |
| tool_limited_sharp | False |
| tool_compatibility | compatible |
| mounting_tab_count | 1 |
| pass_count | 3 |
| cavity_center | (0, 0) |
| passes | [0.25, 0.5, 0.75] |

---

## 12. Warnings and Failure Modes

*No warnings in strategy package.*

### Potential Failure Modes

- **Cavity too shallow:** Pickup may sit proud of the body face
- **Cavity too deep:** Residual material under the cavity may be insufficient
- **Corner too tight:** A cutter that claims final walls must fit the positive corner radius
- **Oversized cutter:** Tool diameter larger than cavity length or width is rejected, not accommodated
- **Floating mounting tab:** Tabs that do not touch the main cavity envelope are rejected
- **Overcut depth:** Pass calculation must never exceed requested final depth

---

## 13. Operator Sign-Off

I have reviewed this strategy package and confirm:

- [ ] All parameters match the intended instrument specification
- [ ] I understand this is advisory only and does not authorize execution
- [ ] I will perform independent verification before machining
- [ ] I accept responsibility for downstream CAM and execution decisions

**Operator Name:** _________________________________

**Date:** _________________________________

**Signature:** _________________________________

---

*This review packet was generated by CAM Assist Blueprint.*
*It is advisory only and does not constitute execution authority.*
