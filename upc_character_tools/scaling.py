"""Resize the bundled Manny part, including its mesh and skin bind pose."""
from contextlib import contextmanager
import base64
import json
from pathlib import Path
import struct
import tempfile
import uuid

import numpy as np


def is_distance(name):
    name = name.lower()
    return name != 'length coefficient' and (
        any(word in name for word in ('position', 'length', 'offset', 'size', 'radius', 'ellipsoid'))
        or name.startswith('joint l ')
        or name in {'start vec', 'ortho vec diff', 'connection local',
                    'outer local first', 'outer local second', 'additional local',
                    'lower_limit', 'upper_limit', 'joint width'})


def scale_mesh_asset(asset, factor):
    if asset['type'] == 'mesh':
        raw = bytearray(base64.b64decode(asset['mesh']))
        polygon_size, count = struct.unpack_from('<IQ', raw)
        if polygon_size != 3 or count != 46091 or len(raw) != asset['mesh_size']:
            raise ValueError('The bundled Manny mesh format has changed. Scaling was stopped.')
        positions = np.frombuffer(raw, dtype='<f4', count=count*4, offset=12).reshape(-1, 4)
        if not np.all(positions[:, 3] == 1):
            raise ValueError('Unexpected Manny mesh position format.')
        positions[:, :3] *= factor
        if not np.all(np.isfinite(positions)):
            raise ValueError('Scale is too large for the Manny mesh.')
        asset['mesh'] = base64.b64encode(raw).decode('ascii')
    elif asset['type'] == 'mesh_dependency':
        raw = bytearray(base64.b64decode(asset['dependency']))
        count = struct.unpack_from('<Q', raw)[0]
        if count != 46091 or len(raw) != asset['dependency_size']:
            raise ValueError('The bundled Manny skin format has changed. Scaling was stopped.')
        offset = 8
        for _ in range(count):
            weights = struct.unpack_from('<Q', raw, offset)[0]
            if weights > 89:
                raise ValueError('Unexpected Manny skin weights.')
            offset += 8 + weights*8
        matrices = struct.unpack_from('<Q', raw, offset)[0]
        offset += 8
        if matrices != 89 or len(raw) != offset + matrices*64:
            raise ValueError('Unexpected Manny inverse bind matrices.')
        # Serialized Eigen matrices are column-major; row 3 holds translation.
        values = np.frombuffer(raw, dtype='<f4', count=matrices*16, offset=offset).reshape(-1, 4, 4)
        values[:, 3, :3] *= factor
        asset['dependency'] = base64.b64encode(raw).decode('ascii')
    else:
        raise ValueError('Unexpected asset in the bundled Manny part.')


def resize_part(document, factor):
    for obj in document['objects'][1:]:
        for data in obj['data']:
            if data['mode'] != 'static' or not is_distance(data['name']):
                continue
            key = str(data['index'])
            value = document['statics'][key]
            if data['type'] == 'Vector3f':
                document['statics'][key] = {axis: number*factor for axis, number in value.items()}
            elif data['type'] == 'float':
                document['statics'][key] = value*factor
        for behaviour in obj['behaviours']:
            if behaviour['type'] == 'RigInfo':
                proto = json.loads(behaviour['proto_json'])
                for joint in proto['JointsLocalData']:
                    position = joint['LocalData']['Position']
                    joint['LocalData']['Position'] = {axis: number*factor for axis, number in position.items()}
                behaviour['proto_json'] = json.dumps(proto)
    replacements = {}
    for asset in document['assets']:
        old_id = asset['id']
        asset['id'] = replacements[old_id] = str(uuid.uuid4())
        scale_mesh_asset(asset, factor)
    # Distinct assets keep differently sized characters independent in one scene.
    for obj in document['objects']:
        for behaviour in obj['behaviours']:
            for key, value in behaviour.items():
                if isinstance(value, str) and value in replacements:
                    behaviour[key] = replacements[value]


@contextmanager
def character_part(here, default_part, factor):
    if factor == 1:
        yield default_part
        return
    sources = (here.parent/'assets'/'manny.partscasc', here.parent.parent/'parts'/default_part)
    source = next((path for path in sources if path.is_file()), None)
    if source is None:
        raise ValueError('The bundled Manny part was not found. Reinstall Manny Tools.')
    document = json.loads(source.read_text(encoding='utf-8'))
    resize_part(document, factor)
    with tempfile.TemporaryDirectory(prefix='manny-scale-') as folder:
        path = Path(folder)/'manny.partscasc'
        path.write_text(json.dumps(document, separators=(',', ':')), encoding='utf-8')
        yield path.as_posix()


def scale_animation(scene, objects, update, factor):
    if factor == 1:
        return
    import csc
    viewer = scene.data_viewer()
    frames = {0, scene.get_current_frame()}
    for obj in objects:
        for data in viewer.get_all_data_id(obj):
            node = update.get_node_by_id(data)
            if node.mode() != csc.model.DataMode.Animation:
                continue
            kind = node.data_type_name()
            if is_distance(viewer.get_data_name(data)) and kind in ('Vector3f', 'float'):
                value = node.value(0)*factor
                for frame in frames:
                    node.set_value(value, frame)
            elif kind == 'Matrix4f':
                matrix = np.array(node.value(0), copy=True)
                matrix[:3, 3] *= factor
                for frame in frames:
                    node.set_value(matrix, frame)
