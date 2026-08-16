# Design-Around Attack — INV_V3_001

**Attack strength**: MODERATE
**Can survive**: True

## 5 Competitor Workarounds

### 1. remove_element
**Description**: Remove the calibration chamber entirely and rely on factory calibration only
**Competitor achieves value**: False

### 2. replace_element
**Description**: Replace the pressure equalization valve with a mechanical compensation system
**Competitor achieves value**: True

### 3. move_element
**Description**: Move the pressure equalization valve to a different location in the system
**Competitor achieves value**: True

### 4. change_material
**Description**: Use different materials for the calibration chamber that are less affected by environmental factors
**Competitor achieves value**: True

### 5. change_control_logic
**Description**: Implement software-based calibration correction instead of hardware-based pressure equalization
**Competitor achieves value**: True

## Survival Path

Refine the claim to specifically define the unique arrangement and interaction between the calibration chamber and pressure equalization valve to prevent design-arounds.

## Rule

Generate 5 workarounds: remove_element, replace_element, move_element, change_material, change_control_logic. If competitor still achieves economic value, DESIGN_AROUND_RISK = HIGH.