# Design-Around Attack — INV_V3_007

**Attack strength**: MODERATE
**Can survive**: False

## 5 Competitor Workarounds

### 1. remove_element
**Description**: Remove the optical filter array entirely and rely on signal processing algorithms to compensate for low perfusion conditions
**Competitor achieves value**: True

### 2. replace_element
**Description**: Replace the optical filter array with a different type of filtering technology (e.g., electronic filtering) that achieves similar results
**Competitor achieves value**: True

### 3. move_element
**Description**: Move the optical filter array to a different position in the optical path between the light source and the detector
**Competitor achieves value**: True

### 4. change_material
**Description**: Change the material composition of the optical filter array to optimize for different wavelengths or perfusion conditions
**Competitor achieves value**: True

### 5. change_control_logic
**Description**: Implement adaptive control logic that adjusts the PPG sensor parameters based on detected perfusion conditions, reducing the need for specialized optical filtering
**Competitor achieves value**: True

## Survival Path

The claim could be strengthened by adding limitations that specifically define the relationship between the optical filter array and the PPG sensor, making it more difficult to design around.

## Rule

Generate 5 workarounds: remove_element, replace_element, move_element, change_material, change_control_logic. If competitor still achieves economic value, DESIGN_AROUND_RISK = HIGH.