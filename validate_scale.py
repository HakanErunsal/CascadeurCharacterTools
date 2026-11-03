"""Run inside Cascadeur's Python Console: exec(open('/path/validate_scale.py').read())."""
import importlib
from pathlib import Path
import tempfile

import csc
import numpy as np
from upc_character_tools import core

importlib.reload(core)
app = csc.app.get_application()
manager = app.get_scene_manager()
original = app.current_scene()
view = manager.create_application_scene()
manager.set_current_scene(view)
scene = view.domain_scene()


def joints(rig, frame=0):
    return {scene.model_viewer().get_object_name(j).split(':')[-1]: core.pose(scene, j, frame)
            for j in rig['joints']}


def mesh_positions(rig):
    bv = scene.behaviour_viewer()
    mesh = next(o for o in rig['objects'] if not bv.get_behaviour_by_name(o, 'MeshObject').is_null())
    return np.asarray(csc.domain.calc_skinned_mesh(scene, mesh, 0).positions)[:, :3]


try:
    offset = np.array([120.0, -200.0, 0.0])
    scene_offset = offset[[0, 2, 1]]
    baseline = core.add_character(scene, 'Default', offset, 135.0)
    def extend_animation(model, update, su):
        for layer in scene.layers_viewer().layer_ids_by_obj_ids(list(baseline['objects'])):
            model.layers_editor().set_fixed_interpolation_or_key_if_need(layer, 7, True)
        model.fit_animation_size_by_layers()
        su.generate_update()
        su.run_update(set(), 7)
    assert scene.modify_update('Extend validation animation', extend_animation)
    reference = joints(baseline)
    reference_mesh = mesh_positions(baseline)
    maximum_joint_error = maximum_mesh_error = 0.0
    for factor in (0.5, 1.5, 2.0):
        scene.set_current_frame(7)
        rig = core.add_character(scene, 'Size_'+str(factor).replace('.', '_'), offset, 135.0, factor)
        core.validate_manny(scene, rig)
        for frame in (0, 7):
            for name, (position, orientation) in joints(rig, frame).items():
                expected = (reference[name][0]-scene_offset)*factor + scene_offset
                error = float(np.max(np.abs(position-expected)))
                maximum_joint_error = max(maximum_joint_error, error)
                assert error < .003, (factor, frame, name, error)
                assert np.allclose(orientation, reference[name][1], atol=2e-4), name
        actual_mesh = mesh_positions(rig)
        expected_mesh = (reference_mesh-scene_offset)*factor + scene_offset
        error = float(np.max(np.abs(actual_mesh-expected_mesh)))
        maximum_mesh_error = max(maximum_mesh_error, error)
        assert error < .005, (factor, 'mesh', error)
        bv, dv = scene.behaviour_viewer(), scene.data_viewer()
        for joint in rig['joints']:
            transform = bv.get_behaviour_by_name(joint, 'Transform')
            data = bv.get_behaviour_data(transform, 'local_scale')
            assert np.allclose(dv.get_data_value(data, 0), [1, 1, 1], atol=1e-5)
        with tempfile.TemporaryDirectory(prefix='manny-export-validation-') as folder:
            report = core.export_character(scene, Path(folder)/'scaled.fbx', rig, 0, 2)
            assert report['bone_count'] == 89 and report['frames'] == 3, report
        assert np.allclose(mesh_positions(baseline), reference_mesh, atol=.003, rtol=0), 'Another Manny mesh changed.'
    before = set(scene.model_viewer().get_objects())
    for invalid in (0, -1, float('nan'), float('inf'), float('-inf')):
        try:
            core.add_character(scene, 'Invalid', scale=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(('Accepted invalid scale', invalid))
        assert set(scene.model_viewer().get_objects()) == before
    print('PASS: sizes 0.5, 1.5, 2; yaw and centimetre offset; frames 0 and 7; all 89 joints; '
          'mesh skinning; unit bone scales; three-frame FBX export; independent characters; '
          'invalid scales.')
    print('Maximum joint error (cm):', maximum_joint_error)
    print('Maximum mesh error (cm):', maximum_mesh_error)
finally:
    manager.set_current_scene(original)
    manager.remove_application_scene(view)
