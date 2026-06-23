# Stage 02 assumptions and limitations

## Component-order decision

- Motive Bone Rotation columns are labeled **X, Y, Z, W**.
- SciPy `Rotation.from_quat` expects **[x, y, z, w]** (scalar-last).
- Therefore the intended mapping is **Motive X,Y,Z,W -> SciPy x,y,z,w**.
- This is a **component-order / library-compatibility** decision, not a full convention proof.

## Explicit limitations

- Intended mapping: Motive X,Y,Z,W -> SciPy x,y,z,w.
- This does not validate quaternion norms, temporal continuity, gaps, or relative joint rotations.
- Alternative-order constructability ([w,x,y,z] fed to SciPy) is reported for comparison only; numerical constructability of both orders does not prove semantic correctness.
- This does not validate global quaternion quality or biomechanical correctness.
