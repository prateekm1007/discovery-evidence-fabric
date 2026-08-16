# Design-Around Attack — INV_V3_002

**Attack strength**: MODERATE
**Can survive**: True

## 5 Competitor Workarounds

### 1. remove_element
**Description**: Eliminate the adjustable cavity design and use a fixed position for the reference pressure sensor
**Competitor achieves value**: False

### 2. replace_element
**Description**: Replace the adjustable cavity design with software-based calibration algorithms that compensate for drift without mechanical adjustment
**Competitor achieves value**: True

### 3. move_element
**Description**: Integrate the reference pressure sensor directly into the cuff structure without a separate adjustable cavity
**Competitor achieves value**: False

### 4. change_material
**Description**: Use different materials for the cuff that maintain consistent positioning without mechanical adjustment
**Competitor achieves value**: False

### 5. change_control_logic
**Description**: Implement periodic recalibration routines that account for drift without physical adjustment of the sensor position
**Competitor achieves value**: True

## Survival Path

Refine the claim to specifically require mechanical adjustment of the sensor position rather than just compensation for drift through any means.

## Rule

Generate 5 workarounds: remove_element, replace_element, move_element, change_material, change_control_logic. If competitor still achieves economic value, DESIGN_AROUND_RISK = HIGH.