# Manny Character Tools for Cascadeur 2026.2

This panel is built for multi-character UE5 Manny animation scenes. It adds a complete copy of Cascadeur's bundled **UE5 Manny Simple** character and exports one selected character as a clean Unreal-ready FBX without changing the animation in the `.casc` scene.

## Install

1. Close Cascadeur, or leave it open and restart it after installation.
2. Double-click `Install.exe`.
3. Select the folder containing `cascadeur.exe` when prompted.
4. Start Cascadeur and open **Scripts > Manny Tools > Character Panel**.

The installer validates the selected Cascadeur folder and copies a self-contained version of the tool into it. The project folder can be moved or deleted after installation. `Install.cmd` remains available as a fallback.

## Add Character

Enter a unique name such as `Enemy_02`, optionally enter an initial Unreal X/Y/Z offset in centimetres, a yaw angle in degrees, and a uniform **Scale**, then click **Add Character**. X/Y/Z and yaw default to `0`; scale defaults to `1`. For example, `X 0, Y 200, Z 0, Yaw 180, Scale 2` adds a character twice Manny's size, places it 200 cm along Unreal Y, and turns it around. Scale must be a finite number greater than zero; an empty scale field uses `1`. The operation:

- inserts the full UE5 Manny Simple mesh, 89-joint skeleton, point rig, and AutoPosing setup;
- prefixes the character's objects with the chosen name;
- resizes, places, and turns the complete character, including its mesh, skeleton, AutoPosing controls, and collision shapes;
- groups the character in the Outliner;
- recreates the bundled Manny track layout inside a named track folder;
- remains one undoable Cascadeur operation.

The name must start with a letter and may contain letters, numbers, spaces, `_`, or `-`.

Scale changes the new character's physical dimensions before placement. It leaves other characters unchanged and keeps bone transform scales at `1`. Export Selected preserves the resized skeleton and mesh; use a matching skeleton or retarget the animation in Unreal when its proportions differ from your target. The location offset stays in centimetres regardless of scale.

## Export Selected

1. Select any mesh, skeleton joint, point control, or AutoPosing control belonging to one character.
2. Select the required frame interval in the Timeline.
3. Keep **Body facing → root motion** for paired execution animations and click **Export Selected**.
4. Leave **FPS** empty to write the scene's frame rate into the FBX, or type one to force it. The export stops if it cannot read the scene setting or if the baked FBX disagrees with it.
5. Choose an FBX filename. Reusing a name safely replaces the older export after the new file passes validation.

The exporter finds the complete character automatically, exports all 89 joints plus the skeletal mesh wrapper, moves the first root position to the origin, and makes the starting body direction neutral while retaining the motion that follows. The operation restores the original object selection, timeline selection, and current frame. It does not save or modify the source `.casc` file.

Use **Use existing root heading** when the root joint itself already contains the heading you want to normalize. The body-facing mode is the intended default for the offset/turned second character in paired animations.

Every FBX receives an adjacent `.export.json` report containing the source character, frame interval, original starting transform, detected heading, frame rate, and normalized root path. For saved scenes, the export dialog defaults to the current `.casc` file's folder and filename, with an `.fbx` extension. For unsaved scenes, exports default to `Documents/CascadeurCharacterTools/Exports` for the current Windows user. If Documents is unavailable, the tool tries Downloads and then the user profile folder.

The wrapper node is written to the FBX as `SKM_Manny_Simple` whatever the character is called in the scene, so a renamed character imports against the same Unreal skeleton. If validation rejects the FBX, the message names the missing bones, the duplicated bones, and any unexpected nodes, and the unvalidated file is kept next to the target as `.failed_raw.fbx` so you can open it and see what Cascadeur produced.

## Nativize Selected

Live Link to Unreal needs the joint names to match the Unreal skeleton exactly (`root`, `pelvis`, `clavicle_l`). A character added with this panel carries its name as a prefix (`Player:clavicle_l`), and Cascadeur's Live Link sender corrupts some of those names on the way out, which shows up in the Unreal log as `Track with name Player:clavicle_l does not exist`.

1. Select any joint, mesh, point, or AutoPosing control belonging to the character.
2. Click **Nativize Selected**.
3. Disconnect and reconnect the Live Link source so Cascadeur resends the bone list.

The tool finds the whole character from the selection and removes the prefix from every one of its objects in one undoable operation. It stops if another object in the scene already uses one of the resulting names, so keep one native character per scene. Export Selected and Add Character keep working on a nativized character.

## Scope

This version deliberately accepts only Cascadeur's bundled UE5 Manny Simple skeleton: exactly 89 uniquely named joints. It stops with a clear message for mixed-character selections, incomplete rigs, non-unit bone transform scales, or invalid ranges. Characters resized with Add Character retain unit bone scales and can be exported.

