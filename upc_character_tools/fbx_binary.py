"""Small lossless FBX binary editor; unchanged properties retain their original bytes."""
from __future__ import annotations
import struct
import zlib
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class Property:
    kind: str
    value: object
    raw: bytes | None = None

    def encode(self):
        if self.raw is not None:
            return self.raw
        k, v = self.kind, self.value
        if k in 'YCLIFD':
            return k.encode() + struct.pack('<' + dict(Y='h', C='?', L='q', I='i', F='f', D='d')[k], v)
        if k in 'SR':
            b = v.encode('utf-8') if k == 'S' else v
            return k.encode() + struct.pack('<I', len(b)) + b
        fmt = dict(f='f', d='d', l='q', i='i', b='?', c='b')[k]
        b = struct.pack('<' + str(len(v)) + fmt, *v)
        packed = zlib.compress(b)
        return k.encode() + struct.pack('<III', len(v), 1, len(packed)) + packed

@dataclass
class Node:
    name: str
    properties: list = field(default_factory=list)
    children: list = field(default_factory=list)
    terminated: bool = False

    @property
    def values(self):
        return [p.value for p in self.properties]

    def child(self, name):
        return next((n for n in self.children if n.name == name), None)

    def set_value(self, index, value):
        self.properties[index] = Property(self.properties[index].kind, value)

class Document:
    def __init__(self, path):
        data = Path(path).read_bytes()
        if not data.startswith(b'Kaydara FBX Binary  \x00\x1a\x00'):
            raise ValueError('Binary FBX required. Set Cascadeur FBX format to Binary.')
        self.version = struct.unpack_from('<I', data, 23)[0]
        self.header = data[:27]
        self.fmt = '<QQQB' if self.version >= 7500 else '<IIIB'
        self.hs = struct.calcsize(self.fmt)

        def parse(pos):
            end, count, plen, nlen = struct.unpack_from(self.fmt, data, pos)
            pos += self.hs
            if not end:
                return None, pos
            if end > len(data) or end <= pos:
                raise ValueError('Invalid FBX node boundary')
            name = data[pos:pos+nlen].decode(); pos += nlen
            prop_end = pos + plen
            properties = []
            for _ in range(count):
                start = pos; k = chr(data[pos]); pos += 1
                if k in 'YCLIFD':
                    f = dict(Y='h', C='?', L='q', I='i', F='f', D='d')[k]
                    value = struct.unpack_from('<'+f, data, pos)[0]; pos += struct.calcsize(f)
                elif k in 'SR':
                    n = struct.unpack_from('<I', data, pos)[0]; pos += 4
                    value = data[pos:pos+n]; pos += n
                    if k == 'S': value = value.decode('utf-8')
                elif k in 'fdlibc':
                    n, enc, size = struct.unpack_from('<III', data, pos); pos += 12
                    b = data[pos:pos+size]; pos += size
                    if enc == 1: b = zlib.decompress(b)
                    elif enc != 0: raise ValueError('Unknown FBX array encoding')
                    f = dict(f='f', d='d', l='q', i='i', b='?', c='b')[k]
                    value = list(struct.unpack('<'+str(n)+f, b))
                else:
                    raise ValueError('Unsupported FBX property '+k)
                properties.append(Property(k, value, data[start:pos]))
            if pos != prop_end: raise ValueError('Invalid FBX property length')
            children = []; terminated = False
            while pos < end:
                n, pos = parse(pos)
                if n is None:
                    terminated = True
                    break
                children.append(n)
            if pos != end: raise ValueError('Invalid FBX child boundary')
            return Node(name, properties, children, terminated), end

        self.nodes = []; pos = 27
        while True:
            node, pos = parse(pos)
            if node is None: break
            self.nodes.append(node)
        # Standard footer: magic, alignment padding, 4 zero bytes, version, 120 zero bytes, magic.
        self.footer = data[pos:]
        self.objects = self.top('Objects').children
        self.by_id = {n.values[0]: n for n in self.objects if n.properties}
        self.connections = [n.values for n in self.top('Connections').children if n.name == 'C']

    def top(self, name):
        return next(n for n in self.nodes if n.name == name)

    def write(self, path):
        def encode(node, offset):
            name = node.name.encode()
            properties = b''.join(p.encode() for p in node.properties)
            pos = offset + self.hs + len(name) + len(properties)
            children = []
            for child in node.children:
                b = encode(child, pos); children.append(b); pos += len(b)
            if node.terminated:
                children.append(bytes(self.hs)); pos += self.hs
            return struct.pack(self.fmt, pos, len(node.properties), len(properties), len(name)) + name + properties + b''.join(children)
        chunks = [self.header]; pos = len(self.header)
        for node in self.nodes:
            b = encode(node, pos); chunks.append(b); pos += len(b)
        chunks.append(bytes(self.hs)); pos += self.hs
        # Preserve the footer payload while recomputing its 16-byte alignment.
        if len(self.footer) >= 160:
            magic = self.footer[:16]
            tail = self.footer[-144:]
            chunks.append(magic + bytes((-(pos+16)) % 16) + tail)
        else:
            chunks.append(self.footer)
        Path(path).write_bytes(b''.join(chunks))

    def models(self):
        return [n for n in self.objects if n.name == 'Model']

    def parent_ids(self):
        return {c[1]: c[2] for c in self.connections if c[0] == 'OO'}

    def curves(self, model_id, prop_name):
        nodes = [c[1] for c in self.connections if c[0] == 'OP' and c[2] == model_id and c[3] == prop_name]
        if len(nodes) != 1: raise ValueError(f'Expected one animation curve node for {prop_name}')
        return {c[3][-1]: self.by_id[c[1]] for c in self.connections if c[0] == 'OP' and c[2] == nodes[0]}

    def set_curve(self, model_id, prop, axis, values):
        curve = self.curves(model_id, prop)[axis]
        target = curve.child('KeyValueFloat')
        if target is None or len(target.values[0]) != len(values):
            raise ValueError('FBX frame count differs from selected interval')
        target.set_value(0, [float(v) for v in values])
        default = curve.child('Default')
        if default: default.set_value(0, float(values[0]))

def short_name(node):
    return node.values[1].split('\x00')[0].split(':')[-1]

def model_properties(node):
    ps = node.child('Properties70')
    return {p.values[0]: p.values[4:] for p in ps.children if p.name == 'P'} if ps else {}

def set_model_vector(node, name, values):
    ps = node.child('Properties70')
    if ps is None:
        ps = Node('Properties70', terminated=True); node.children.append(ps)
    p = next((p for p in ps.children if p.name == 'P' and p.values[0] == name), None)
    if p:
        for i, v in enumerate(values): p.set_value(4+i, float(v))
    else:
        kind = name if name.startswith('Lcl ') else 'Vector3D'
        ps.children.append(Node('P', [Property('S', name), Property('S', kind), Property('S',''), Property('S','A' if name.startswith('Lcl ') else '')] + [Property('D',float(v)) for v in values]))
