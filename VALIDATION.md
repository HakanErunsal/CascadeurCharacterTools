# Validation record

## v1.0.9 (export at standard size, Details-style panel)

Validated on 2026-11-03:

- Ran the size normalization on a Scale 1.5 export (`AS_UPC_Sword_Execute_A_Victim`). Measured scale was 1.5000000; after normalization every bone rest offset matched the Scale 1 example FBX within 0.000003 cm, and every bone translation key equalled the original divided by 1.5 within 0.000003 cm.
- Rendered the redesigned QML panel with Qt Quick Controls Basic and a stub model; all rows, fields, the dropdown, the checkbox label and the status bar laid out at the default 440 px width.
- Installed with `Install.exe --install` into Cascadeur 2026.2.

## v1.0.8 — character scale

Validated in Cascadeur 2026.2 on 2026-11-03 using isolated scratch scenes:

- Added characters at scale 0.5, 1.5, and 2, with Unreal X/Y offsets and yaw 135 degrees.
- Compared all 89 joint positions and orientations against a default-size character at the same placement, on frames 0 and 7. Maximum position error was 0.000458 cm.
- Compared every skinned mesh position against the expected resized mesh. Maximum error was 0.000435 cm.
- Confirmed all bone transform scales remain `[1, 1, 1]` and the original character's mesh remains unchanged within solver precision.
- Exported frames 0–2 for each resized character through Export Selected; every FBX passed the existing 89-joint, root-motion, and frame-count checks.
- Rejected zero, negative, NaN, and infinite scales before adding scene objects.
- Verified a scaled addition is removed by a single Undo action.
- Opened the QML panel and exercised its actual Add Character button with Scale 2; verified the resulting 341-object character and approximately 323 cm root-to-head height.
- Initialized additions at frame 0 and restored the current frame, including when adding at frame 7.

Run `validate_scale.py` inside Cascadeur to repeat the numerical, mesh, export, and invalid-input checks. The script creates a scratch scene and restores the previously active scene when finished.

Resized exports retain their resized skeleton and mesh. Retargeting and playback against a different Unreal skeleton remain project-specific.

## Original release validation

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
