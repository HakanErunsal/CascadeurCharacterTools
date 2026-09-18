"""Manny scene insertion and export without editing source animation."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import tempfile
import numpy as np
import csc
from .fbx_binary import Document, short_name, model_properties, set_model_vector

HERE = Path(__file__).parent
REFERENCE = json.loads((HERE / 'reference.json').read_text())
TRACKS = json.loads((HERE / 'tracks.json').read_text())
PART = 'upc_character_tools/manny.partscasc'

def view_for(scene):
    for view in csc.app.get_application().get_scene_manager().scenes():
        if view.domain_scene() == scene:
            return view
    raise ValueError('The source scene is no longer open.')

def parent_of(scene, obj):
    bv = scene.behaviour_viewer()
    b = bv.get_behaviour_by_name(obj, 'Basic')
    return bv.get_behaviour_object(b, 'parent') if not b.is_null() else csc.model.ObjectId.null()

def characters(scene):
    mv, bv = scene.model_viewer(), scene.behaviour_viewer()
    result = []
    for rig in bv.get_behaviours('RigInfo'):
        owner = bv.get_behaviour_owner(rig)
        joints = set(bv.get_behaviour_objects_range(rig, 'related_joints'))
        roots = [j for j in joints if mv.get_object_name(j).split(':')[-1] == 'root']
        if len(roots) != 1:
            continue
        root = roots[0]
        nm = mv.get_object_name(root)
        wrapper = parent_of(scene, root)
        label = nm.rsplit(':', 1)[0] if ':' in nm else (
            mv.get_object_name(wrapper) if not wrapper.is_null() else 'Manny')
        objects = set(bv.get_behaviour_objects_range(rig, 'rig_objects')) | joints | {owner}
        for j in list(objects):
            seen = set()
            while not j.is_null() and j not in seen:
                seen.add(j); objects.add(j); j = parent_of(scene, j)
        for mesh in bv.get_behaviours('MeshObject'):
            if joints.intersection(bv.get_behaviour_objects_range(mesh, 'linked_objects')):
                objects.add(bv.get_behaviour_owner(mesh))
        result.append(dict(rig=rig, owner=owner, joints=joints, root=root, label=label, objects=objects))
    return result

def resolve_character(scene):
    rigs = characters(scene)
    selected = set(scene.selector().selected().ids)
    if not selected:
        raise ValueError('Select a joint, mesh, point, or AutoPosing control on one character.')
    found = set()
    for entity in selected:
        matches = {i for i, rig in enumerate(rigs) if entity in rig['objects']}
        if not matches:
            try:
                ri = csc.domain.find_actual_rig_info_id(scene, {entity})
                matches = {i for i, rig in enumerate(rigs) if rig['rig'] == ri}
            except (RuntimeError, TypeError):
                matches = set()
        if not matches:
            raise ValueError('Part of the selection does not belong to a Manny character. Select only that character.')
        found.update(matches)
    if len(found) != 1:
        raise ValueError('The selection spans multiple characters. Select one character to export.')
    return rigs[next(iter(found))]

def validate_manny(scene, rig):
    names = [scene.model_viewer().get_object_name(j).split(':')[-1] for j in rig['joints']]
    if len(names) != len(set(names)) or sorted(names) != REFERENCE['bones']:
        raise ValueError('This rig differs from the bundled UE5 Manny Simple skeleton (89 joints). Export was stopped.')

def add_character(scene, name, offset=(0.0, 0.0, 0.0), yaw_degrees=0.0):
    name = name.strip()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_ -]{0,47}', name):
        raise ValueError('Use a name starting with a letter, followed by letters, numbers, spaces, _ or - (48 characters maximum).')
    if name in {r['label'] for r in characters(scene)}:
        raise ValueError('That character name is already in this scene.')
    offset = np.asarray(offset, dtype=float)
    yaw_degrees = float(yaw_degrees)
    if offset.shape != (3,) or not np.all(np.isfinite(offset)) or not math.isfinite(yaw_degrees):
        raise ValueError('Initial position and yaw must contain finite numbers.')
    # Inputs follow Unreal's X/Y/Z convention. Cascadeur is Y-up, so Unreal
    # Y maps to Cascadeur Z and Unreal Z maps to Cascadeur Y.
    scene_offset = np.asarray([offset[0], offset[2], offset[1]], dtype=float)
    before = set(scene.model_viewer().get_objects())
    new_rig = {}
    def mod(model, update, su, session):
        lv = scene.layers_viewer()
        root_folder = lv.root_id()
        ids, groups = csc.parts.Buffer.get().insert_objects_by_path(PART, update.root().group_id(), model, scene.assets_manager())
        if len(ids) != 341:
            raise RuntimeError('Manny template did not insert completely.')
        mv, bv = scene.model_viewer(), scene.behaviour_viewer()
        object_keys = {mv.get_object_name(j)+'|'+str(not bv.get_behaviour_by_name(j,'MeshObject').is_null()):j for j in ids}
        top_rig = next(j for j in ids if mv.get_object_name(j).split(':')[-1] == 'Rig(0)')
        for j in ids:
            old = mv.get_object_name(j).split(':')[-1]
            model.set_object_name(j, name if j == top_rig else f'{name}:{old}')
        # Basic.parent controls outliner organization; existing transform graph stays connected.
        for j in ids:
            # Keep FBX-exportable roots at scene level. A Basic-only Outliner
            # group cannot be represented as their parent in FBX.
            export_behaviour = bv.get_behaviour_by_name(j, 'FbxExport')
            if j != top_rig and export_behaviour.is_null() and parent_of(scene, j).is_null():
                basic = bv.get_behaviour_by_name(j, 'Basic')
                if not basic.is_null():
                    if not model.behaviour_editor().set_behaviour_model_object(basic, 'parent', top_rig):
                        raise RuntimeError('Unable to group character in the outliner.')
        le = model.layers_editor()
        folder = le.create_folder(name, root_folder, False)
        folders={f['id']:f for f in TRACKS['folders']}
        tracks={t['id']:t for t in TRACKS['tracks']}
        referenced={c for f in folders.values() for c in f['children']}
        template_roots=set(folders)-referenced
        def populate(item_id, target):
            if item_id in tracks:
                track=tracks[item_id]
                lid=le.create_layer(track['name'],target)
                model.move_objects_to_layer([object_keys[k] for k in track['objects']],lid)
            else:
                original=folders[item_id]
                child_folder=le.create_folder(original['name'],target,not bool(original['children']))
                for child in original['children']:populate(child,child_folder)
        for template_root in template_roots:
            for child in folders[template_root]['children']:populate(child,folder)
        su.generate_update(); su.run_update(set(), scene.get_current_frame())
        rig = next(r for r in characters(scene) if r['owner'] in ids)
        validate_manny(scene, rig)
        # Register the inserted controls with Cascadeur's AutoPosing tool. The
        # bundled part already contains all AutoPosing links; tool.add makes
        # them immediately usable in the current scene.
        point_owners = [bv.get_behaviour_owner(b) for b in bv.get_behaviours('Point')]
        point = next((p for p in point_owners if p in rig['objects']), None)
        if point is None:
            raise RuntimeError('The Manny point rig is missing.')
        session.take_selector().select({point}, point, csc.domain.SelectorFilter.Free)
        app = csc.app.get_application()
        viewports = [vp.domain_viewport() for vp in app.current_scene().viewports()]
        viewport_modes = [vp.mode_visualizers() for vp in viewports]
        app.get_tools_manager().get_tool('AutoPosingTool').editor(app.current_scene()).add(session)
        for viewport, mode in zip(viewports, viewport_modes):
            viewport.set_mode_visualizers(csc.view.ViewportMode(mode))
        # Move the AutoPosing controls so the skeleton, mesh, and controls are
        # solved together. The sign change preserves Unreal's positive yaw.
        rotation = yaw_matrix(math.radians(-yaw_degrees))
        changed = set()
        controls = [p for p in point_owners if p in rig['objects'] and
                    bv.get_behaviour_by_name(p, 'LimbDirection').is_null()]
        for control in controls:
            position = update.get_object_by_id(control).root_group().node_deep('Position')
            value = rotation @ np.asarray(position.value(0), dtype=float) + scene_offset
            position.set_value(np.asarray(value, dtype=np.float32), 0)
            changed.add(position.data_id())
        for frame in {0, scene.get_current_frame()}:
            su.run_update(changed, frame)
        session.take_selector().select({rig['root']}, rig['root'], csc.domain.SelectorFilter.Free)
        new_rig.update(rig)
    if not scene.modify_update_with_session('Add Manny: '+name, mod):
        raise RuntimeError('Cascadeur could not add Manny. See the Event Log; the operation was not completed.')
    if len(set(scene.model_viewer().get_objects()) - before) != 341:
        raise RuntimeError('Unexpected character object count after insertion.')
    return new_rig

def nativize_character(scene, rig=None):
    """Strip the character prefix from every object of one character so joint names match the Unreal skeleton."""
    rig = rig or resolve_character(scene)
    mv = scene.model_viewer()
    root_name = mv.get_object_name(rig['root'])
    if ':' not in root_name:
        raise ValueError(f"{rig['label']} already uses native names.")
    prefix = root_name.rsplit(':', 1)[0] + ':'
    names = {o: mv.get_object_name(o) for o in mv.get_objects()}
    targets = {o: n[len(prefix):] for o, n in names.items() if n.startswith(prefix)}
    others = {n for o, n in names.items() if o not in targets}
    clashes = sorted(set(targets.values()) & others)
    if clashes:
        raise ValueError('Another object already uses the native name ' + ', '.join(clashes[:5]) + (' and more' if len(clashes) > 5 else '') + '. Keep one native character per scene.')
    def mod(model, update, su, session):
        for o, name in targets.items():
            model.set_object_name(o, name)
    if not scene.modify_update_with_session('Nativize: ' + rig['label'], mod):
        raise RuntimeError('Cascadeur could not rename the character. See the Event Log; the operation was not completed.')
    return dict(label=rig['label'], count=len(targets))

def yaw_matrix(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]], dtype=float)

def euler_xyz(matrix):
    m = np.asarray(matrix)
    cy = math.hypot(m[0,0], m[1,0])
    if cy > 1e-7:
        return [math.atan2(m[2,1],m[2,2]), math.atan2(-m[2,0],cy), math.atan2(m[1,0],m[0,0])]
    return [math.atan2(-m[1,2],m[1,1]), math.atan2(-m[2,0],cy), 0.0]

def pose(scene, obj, frame):
    bv, dv = scene.behaviour_viewer(), scene.data_viewer()
    tr = bv.get_behaviour_by_name(obj, 'Transform')
    pos = np.array(dv.get_data_value(bv.get_behaviour_data(tr,'global_position'), frame), dtype=float)
    rot = np.array(dv.get_data_value(bv.get_behaviour_data(tr,'global_rotation'), frame).to_rotation_matrix(), dtype=float)
    return pos, rot

def sample_export(scene, rig, first, last, heading_mode):
    root = rig['root']; mv = scene.model_viewer()
    direct = [j for j in rig['joints'] if parent_of(scene,j) == root]
    pelvis = next(j for j in rig['joints'] if mv.get_object_name(j).split(':')[-1] == 'pelvis')
    reference_root = np.array(REFERENCE['root'])
    reference_pelvis = np.array(REFERENCE['pelvis'])
    ref = reference_pelvis if heading_mode == 'body' else reference_root
    facing_obj = pelvis if heading_mode == 'body' else root
    headings = []
    for f in range(first, last+1):
        facing = pose(scene,facing_obj,f)[1] @ ref.T @ np.array([0.,0.,1.])
        if math.hypot(facing[0],facing[2]) < .05:
            if not headings:
                raise ValueError('Starting facing direction is vertical. Choose Root heading or another start frame.')
            headings.append(headings[-1])
        else:
            headings.append(math.atan2(facing[0],facing[2]))
    headings = np.unwrap(headings)
    rotation_delta = yaw_matrix(-headings[0])
    initial_position = pose(scene,root,first)[0]
    # Match the working FBX's Y-up wrapper with a -90 degree X pre-rotation.
    wrapper = np.array([[1.,0,0],[0,0,1],[0,-1,0]])
    transforms = {mv.get_object_name(j).split(':')[-1]: {'position':[],'rotation':[]} for j in [root]+direct}
    expected = []
    for n, f in enumerate(range(first,last+1)):
        p, r = pose(scene,root,f)
        new_p = rotation_delta @ (p-initial_position)
        if heading_mode == 'body':
            new_r = yaw_matrix(headings[n]-headings[0]) @ reference_root
        else:
            # Remove only the starting heading, retaining animated root pitch/roll.
            new_r = rotation_delta @ r
        transforms['root']['position'].append(wrapper.T @ new_p)
        transforms['root']['rotation'].append(euler_xyz(wrapper.T @ new_r))
        expected.append(new_p.tolist())
        for j in direct:
            jp, jr = pose(scene,j,f)
            desired_p = rotation_delta @ (jp-initial_position)
            desired_r = rotation_delta @ jr
            key = mv.get_object_name(j).split(':')[-1]
            transforms[key]['position'].append(new_r.T @ (desired_p-new_p))
            transforms[key]['rotation'].append(euler_xyz(new_r.T @ desired_r))
    for data in transforms.values():
        data['position'] = np.asarray(data['position'])
        data['rotation'] = np.degrees(np.unwrap(np.asarray(data['rotation']),axis=0))
    return transforms, dict(first_frame=first,last_frame=last,heading_mode=heading_mode,
        original_position_cm=initial_position.tolist(),original_heading_degrees=float(math.degrees(headings[0])),
        root_path_cm=expected)

def correct_fbx(raw_path, output, transforms, metadata):
    doc = Document(raw_path)
    axes = model_properties(doc.top('GlobalSettings'))
    if axes.get('UpAxis') != [1] or axes.get('UnitScaleFactor') != [1.0]:
        raise ValueError('Expected Y-up, centimetre FBX output.')
    models = doc.models(); names = [short_name(n) for n in models]
    bones = set(REFERENCE['bones'])
    bone_names = sorted(n for n in names if n in bones)
    others = [n for n in names if n not in bones]
    if bone_names != sorted(bones) or len(others) != 1:
        from collections import Counter
        got, want = Counter(bone_names), Counter(bones)
        missing = sorted((want - got).elements())
        extra = sorted((got - want).elements())
        raise ValueError(
            'FBX does not contain exactly one complete Manny skeleton and its wrapper. '
            f'Found {len(names)} nodes. Missing bones: {missing}. Duplicate bones: {extra}. Non-bone nodes: {others}.')
    by_name = dict(zip(names, models)); parents = doc.parent_ids()
    wrapper = by_name[others[0]]; root = by_name['root']
    if parents.get(root.values[0]) != wrapper.values[0] or parents.get(wrapper.values[0],0) != 0:
        raise ValueError('Unexpected export root hierarchy.')
    names = ['SKM_Manny_Simple' if n == others[0] else n for n in names]
    by_name = dict(zip(names, models))
    for node, name in zip(models, names):
        old = node.values[1]
        node.set_value(1, name + old[old.index('\x00'):])
    for n in models:
        p = model_properties(n)
        if any(abs(x-1) > 1e-4 for x in p.get('Lcl Scaling',[1,1,1])):
            raise ValueError('Scaled rigs are not supported by this Manny export preset.')
    count = metadata['last_frame'] - metadata['first_frame'] + 1
    for prop, vec in [('Lcl Translation',[0,0,0]),('Lcl Rotation',[0,0,0]),('Lcl Scaling',[1,1,1])]:
        set_model_vector(wrapper,prop,vec)
        for i, axis in enumerate('XYZ'):
            doc.set_curve(wrapper.values[0],prop,axis,[vec[i]]*count)
    set_model_vector(wrapper,'PreRotation',[-90,0,0])
    set_model_vector(wrapper,'PostRotation',[0,0,0])
    for name, data in transforms.items():
        node = by_name[name]
        props = model_properties(node)
        if props.get('RotationOrder',[0]) != [0]:
            raise ValueError('Unexpected joint Euler rotation order.')
        for key in ('PreRotation','PostRotation','RotationPivot','RotationOffset','ScalingPivot','ScalingOffset'):
            if any(abs(v)>1e-5 for v in props.get(key,[0,0,0])):
                raise ValueError('Unexpected joint pivot or pre-rotation: '+name)
        for prop, key in [('Lcl Translation','position'),('Lcl Rotation','rotation')]:
            for i, axis in enumerate('XYZ'):
                doc.set_curve(node.values[0],prop,axis,data[key][:,i])
        # Keep bone rest transforms intact. Animation curve defaults are updated independently.
    time = doc.curves(root.values[0],'Lcl Translation')['X'].child('KeyTime').values[0]
    if len(time)!=count or any(b<=a for a,b in zip(time,time[1:])):
        raise ValueError('Export frame times are invalid.')
    t0 = time[0]
    if t0:
        for n in doc.objects:
            if n.name=='AnimationCurve' and n.child('KeyTime'):
                t=n.child('KeyTime');t.set_value(0,[x-t0 for x in t.values[0]])
    doc.write(output)
    # Reparse before delivering, and verify the exact root values and bone list.
    result = Document(output)
    r = next(n for n in result.models() if short_name(n)=='root')
    for prop,key in [('Lcl Translation','position'),('Lcl Rotation','rotation')]:
        curves=result.curves(r.values[0],prop)
        actual=np.column_stack([curves[a].child('KeyValueFloat').values[0] for a in 'XYZ'])
        if not np.allclose(actual,transforms['root'][key],atol=2e-4):
            raise ValueError('Root verification failed after writing FBX.')
    metadata['frames']=count
    metadata['bone_count']=len(REFERENCE['bones'])
    metadata['frame_rate']=round(46186158000/(time[1]-time[0]),6) if count>1 else None

def fbx_frame_rate(path):
    # Autodesk FBX EMode values; this reads timing from the native scene exporter.
    # https://help.autodesk.com/cloudhelp/2020/ENU/FBX-API-Reference/cpp_ref/class_fbx_time.html
    if Path(path).read_bytes()[:20].startswith(b'Kaydara FBX Binary'):
        props=model_properties(Document(path).top('GlobalSettings'))
        mode=int(props['TimeMode'][0]);custom=float(props.get('CustomFrameRate',[0])[0])
    else:
        text=Path(path).read_text(encoding='utf-8-sig')
        m=re.search(r'P:\s*"TimeMode"[^\r\n]*,\s*(\d+)\s*$',text,re.M)
        c=re.search(r'P:\s*"CustomFrameRate"[^\r\n]*,\s*([-+\d.eE]+)\s*$',text,re.M)
        if not m:raise ValueError('Cannot read the scene frame rate from the FBX export.')
        mode=int(m.group(1));custom=float(c.group(1)) if c else 0.0
    rates={1:120,2:100,3:60,4:50,5:48,6:30,7:30,8:30000/1001,9:30000/1001,
           10:25,11:24,12:1000,13:24000/1001,14:custom,15:96,16:72,17:60000/1001,18:120000/1001}
    fps=rates.get(mode,0)
    if fps<=0:raise ValueError('Unsupported or undefined FBX frame rate.')
    return fps

def scene_frame_rate(view):
    """Best-effort read of the scene FPS. Returns None when no known setting form answers; the export then trusts the FBX Cascadeur bakes and reports the measured rate."""
    handler=view.get_setting_handler()
    for getter in (handler.get_float_value,handler.get_int_value):
        for args in (('SceneSettings','FPS'),('Scene','FPS'),('Data','FPS'),('SceneSettings/FPS',),('Scene/FPS',),('Data/FPS',),('FPS',)):
            try:
                fps=float(getter(*args))
                if fps>0:return fps
            except Exception:
                pass
    for owner in (view,csc.app.get_application().get_scene_manager().current_scene()):
        for name in ('get_fps','fps','get_frame_rate','frame_rate'):
            try:
                attr=getattr(owner,name)
                fps=float(attr() if callable(attr) else attr)
                if fps>0:return fps
            except Exception:
                pass
    return None

def scene_fbx_loader(scene,view,fps):
    """The FBX loader Cascadeur's own export uses, which bakes at the scene frame rate. Falls back to a private loader when the tool is unavailable."""
    try:
        tool=csc.app.get_application().get_tools_manager().get_tool('FbxSceneLoader')
        loader=tool.get_fbx_loader(csc.app.get_application().get_scene_manager().current_scene())
        if loader is not None:return loader
    except Exception:
        pass
    return csc.fbx.FbxLoader(fps or 30.0,scene.get_event_log_or_null(),view)

def export_with_clean_wrapper_parent(scene, view, wrapper, loader, path):
    """Export with the skeletal wrapper temporarily detached from UI-only groups."""
    original_parent=parent_of(scene,wrapper)
    if original_parent.is_null():
        loader.export_joints_selected(str(path))
        return
    basic=scene.behaviour_viewer().get_behaviour_by_name(wrapper,'Basic')
    if basic.is_null():
        raise RuntimeError('Manny export wrapper has no Basic hierarchy behaviour.')
    export_error=[]
    def mod(model,update,su,session):
        editor=model.behaviour_editor()
        if not editor.set_behaviour_model_object(basic,'parent',csc.model.ObjectId.null()):
            raise RuntimeError('Could not detach the export wrapper from its Outliner group.')
        su.generate_update();su.run_update(set(),scene.get_current_frame())
        try:
            loader.export_joints_selected(str(path))
        except Exception as error:
            export_error.append(error)
        finally:
            if not editor.set_behaviour_model_object(basic,'parent',original_parent):
                raise RuntimeError('Could not restore the export wrapper to its Outliner group.')
            su.generate_update();su.run_update(set(),scene.get_current_frame())
        if export_error:
            raise export_error[0]
    if not scene.modify_update_with_session('Export Manny (temporary hierarchy)',mod):
        if export_error:
            raise RuntimeError('Cascadeur failed while preparing the Manny hierarchy for export.') from export_error[0]
        raise RuntimeError('Cascadeur could not temporarily prepare the Manny hierarchy for export.')

def export_character(scene, path, rig=None, first=None, last=None, heading_mode='body', fps=None):
    if heading_mode not in ('body','root'):
        raise ValueError('Unknown heading mode.')
    rig = rig or resolve_character(scene)
    validate_manny(scene,rig)
    interval = scene.get_layers_selector().selection().frames_interval()
    if first is None: first=interval.first
    if last is None: last=interval.last
    if first<0 or last<first:
        raise ValueError('Select a valid frame interval.')
    view=view_for(scene)
    if last>view.animation_boundary().last_frame or last>=scene.data_viewer().get_animation_size():
        raise ValueError('Selected interval exceeds the scene animation range.')
    path=Path(path).with_suffix('.fbx')
    report=path.with_suffix('.export.json')
    if not path.parent.is_dir():
        raise ValueError('Choose an existing export folder.')
    transforms,metadata=sample_export(scene,rig,first,last,heading_mode)
    metadata.update(character=rig['label'],source_scene=view.get_path_name())
    old_selection=scene.selector().selected()
    old_ids=set(old_selection.ids)
    old_ordered=list(old_selection.ordered_ids)
    old_pivot=old_ordered[0] if old_ordered else csc.model.ObjectId.null()
    old_frames=scene.get_layers_selector().selection()
    old_frame=scene.get_current_frame()
    old_path=view.get_path_name()
    export_objects=set(rig['joints'])
    p=parent_of(scene,rig['root'])
    if p.is_null(): raise ValueError('Manny export wrapper is missing.')
    export_objects.add(p)
    app=csc.app.get_application()
    if not app.is_export_available():
        raise ValueError('FBX export is unavailable under the current Cascadeur license.')
    # Build beside the destination, then atomically replace an older export
    # only after the new FBX has passed all validation.
    with tempfile.TemporaryDirectory(prefix='upc_manny_',dir=path.parent) as temp:
        raw=Path(temp)/'raw.fbx';fixed=Path(temp)/'normalized.fbx'
        try:
            scene.selector().select(export_objects,rig['root'],csc.domain.SelectorFilter.Free)
            layers=list(scene.layers_viewer().layer_ids_by_obj_ids(list(export_objects)))
            scene.get_layers_selector().set_full_selection_by_parts(layers,first,last)
            requested=float(fps) if fps else None
            detected=scene_frame_rate(view)
            loader=scene_fbx_loader(scene,view,requested or detected)
            settings=csc.fbx.FbxSettings()
            settings.mode=csc.fbx.FbxSettingsMode.Binary
            settings.up_axis=csc.fbx.FbxSettingsAxis.Y
            settings.bake_animation=True
            settings.apply_euler_filter=True
            loader.set_settings(settings)
            export_with_clean_wrapper_parent(scene,view,p,loader,raw)
        finally:
            scene.selector().select(old_ids,old_pivot,csc.domain.SelectorFilter.Free)
            scene.get_layers_selector().set_full_selection_by_parts(old_frames)
            if scene.get_current_frame()!=old_frame:scene.set_current_frame(old_frame)
        if view.get_path_name()!=old_path:
            raise RuntimeError('Source scene path unexpectedly changed.')
        if not raw.is_file() or raw.stat().st_size<100:
            raise RuntimeError('Cascadeur did not produce an FBX. Check the Event Log.')
        try:
            correct_fbx(raw,fixed,transforms,metadata)
        except ValueError:
            import shutil
            shutil.copy2(raw,path.with_suffix('.failed_raw.fbx'))
            raise
        measured=metadata.get('frame_rate')
        metadata['frame_rate_requested']=requested
        metadata['frame_rate_detected']=detected
        if requested and measured and abs(measured-requested)>0.01:
            raise RuntimeError(f"The scene is at {measured:g} fps, not {requested:g}. Set Frame rate to {requested:g} in Scene Settings (the timeline fps field is display only) and export again.")
        temporary_report=Path(temp)/'normalized.export.json'
        temporary_report.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        os.replace(fixed,path)
        os.replace(temporary_report,report)
    return metadata
