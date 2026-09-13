# Validation record

Tested with Cascadeur 2026.2.0.16422 on this machine and the project scene:

`AS_Unarmed_Execution.casc`

- Detected both characters as complete, independent 89-joint UE5 Manny rigs.
- Resolved each character from its mesh, a skeleton joint, and a point control.
- Rejected a selection spanning both characters.
- Built a scratch scene containing ten complete named Manny characters: 3,410 scene objects and 750 AutoPosing links.
- Exercised the actual **Add Character** button in the QML panel.
- Exported the enemy from frames 20–40 and re-imported the FBX into Cascadeur.
- Verified 21 frames at 30 fps and exactly 89 joints.
- Verified the exported root starts at `[0, 0, 0]`.
- Compared the re-imported pose against the transformed source at frames 0, 1, 7, and 20. Maximum position difference was 0.00025 cm; maximum non-root rotation-matrix element difference was 0.0000033.
- Re-imported the full 96-frame example and sampled frames 0, 1, 30, 60, and 95. Maximum position difference was 0.00034 cm; maximum non-root rotation-matrix element difference was 0.0000046.
- Matched the known-good attacker A file's export structure: 90 FBX models (89 joints plus wrapper), Y-up axis, centimetre units, and 96 frames.
- Verified that object selection, Timeline interval, current frame, and source scene path are restored after export.
- Verified that the source `.casc` file on disk was not overwritten.

The example FBX in `Examples` is the normalized second character from frames 0–95. Final Unreal import settings and in-engine playback remain project-specific and should be checked in the target Unreal project before replacing production animation assets.
