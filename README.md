# Manny Character Tools for Cascadeur 2026.2

This panel is built for multi-character UE5 Manny animation scenes. It adds a complete copy of Cascadeur's bundled **UE5 Manny Simple** character and exports one selected character as a clean Unreal-ready FBX without changing the animation in the `.casc` scene.

## Install

1. Close Cascadeur, or leave it open and restart it after installation.
2. Double-click `Install.exe`.
3. Select the folder containing `cascadeur.exe` when prompted.
4. Start Cascadeur and open **Scripts > Manny Tools > Character Panel**.

The installer validates the selected Cascadeur folder and copies a self-contained version of the tool into it. The project folder can be moved or deleted after installation. `Install.cmd` remains available as a fallback.

## Add Character

Enter a unique name such as `Enemy_02`, optionally enter an initial Unreal X/Y/Z offset in centimetres and a yaw angle in degrees, then click **Add Character**. All four transform fields default to `0`, so `X 0, Y 200, Z 0, Yaw 180` places the second character 200 cm along Unreal Y and turns it around. The operation:

- inserts the full UE5 Manny Simple mesh, 89-joint skeleton, point rig, and AutoPosing setup;
- prefixes the character's objects with the chosen name;
- places and turns the complete character, including its mesh, skeleton, and AutoPosing controls;
- groups the character in the Outliner;
- recreates the bundled Manny track layout inside a named track folder;
- remains one undoable Cascadeur operation.

The name must start with a letter and may contain letters, numbers, spaces, `_`, or `-`.

## Export Selected

1. Select any mesh, skeleton joint, point control, or AutoPosing control belonging to one character.
2. Select the required frame interval in the Timeline.
3. Keep **Body facing → root motion** for paired execution animations and click **Export Selected**.
4. Choose an FBX filename. Reusing a name safely replaces the older export after the new file passes validation.

The exporter finds the complete character automatically, exports all 89 joints plus the skeletal mesh wrapper, moves the first root position to the origin, and makes the starting body direction neutral while retaining the motion that follows. The operation restores the original object selection, timeline selection, and current frame. It does not save or modify the source `.casc` file.

Use **Use existing root heading** when the root joint itself already contains the heading you want to normalize. The body-facing mode is the intended default for the offset/turned second character in paired animations.

Every FBX receives an adjacent `.export.json` report containing the source character, frame interval, original starting transform, detected heading, frame rate, and normalized root path. Exports made from the panel default to the `Exports` folder beside this README.

## Scope

This version deliberately accepts only Cascadeur's bundled UE5 Manny Simple skeleton: exactly 89 uniquely named joints. It stops with a clear message for mixed-character selections, incomplete rigs, scaled rigs, or invalid ranges.
