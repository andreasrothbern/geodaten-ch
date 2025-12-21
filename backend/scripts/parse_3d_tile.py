#!/usr/bin/env python3
"""
3D Tiles Parser - Proof of Concept
==================================

Lädt und analysiert ein swissBUILDINGS3D 3D Tile (.b3dm Format).
Extrahiert Gebäudehöhen (Traufe, First) aus der 3D-Geometrie.

3D Tiles Format:
- .b3dm = Batched 3D Model (Header + FeatureTable + BatchTable + glTF)
- glTF enthält die 3D-Geometrie als Mesh
- BatchTable enthält Attribute wie EGID
"""

import struct
import json
import gzip
from pathlib import Path
from io import BytesIO
import urllib.request
import sys

# 3D Tiles Base URL
TILES_BASE_URL = "https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/20251121"


def download_tile(tile_path: str) -> bytes:
    """
    Lädt ein 3D Tile herunter.

    Args:
        tile_path: Pfad wie "11/1891/425.b3dm"

    Returns:
        Rohe Bytes des Tiles
    """
    url = f"{TILES_BASE_URL}/{tile_path}"
    print(f"Downloading: {url}")

    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; geodaten-ch/1.0)',
        'Accept-Encoding': 'gzip'
    })

    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()

        # Prüfen ob gzip-komprimiert
        if data[:2] == b'\x1f\x8b':
            data = gzip.decompress(data)

        print(f"Downloaded {len(data):,} bytes")
        return data


def parse_b3dm_header(data: bytes) -> dict:
    """
    Parst den b3dm Header.

    b3dm Header (28 bytes):
    - magic (4 bytes): "b3dm"
    - version (4 bytes): uint32
    - byteLength (4 bytes): uint32
    - featureTableJSONByteLength (4 bytes): uint32
    - featureTableBinaryByteLength (4 bytes): uint32
    - batchTableJSONByteLength (4 bytes): uint32
    - batchTableBinaryByteLength (4 bytes): uint32
    """
    if len(data) < 28:
        raise ValueError(f"Data too short for b3dm header: {len(data)} bytes")

    magic = data[0:4].decode('ascii')
    if magic != 'b3dm':
        raise ValueError(f"Invalid magic: {magic}, expected 'b3dm'")

    version = struct.unpack('<I', data[4:8])[0]
    byte_length = struct.unpack('<I', data[8:12])[0]
    feature_table_json_length = struct.unpack('<I', data[12:16])[0]
    feature_table_binary_length = struct.unpack('<I', data[16:20])[0]
    batch_table_json_length = struct.unpack('<I', data[20:24])[0]
    batch_table_binary_length = struct.unpack('<I', data[24:28])[0]

    return {
        'magic': magic,
        'version': version,
        'byteLength': byte_length,
        'featureTableJSONByteLength': feature_table_json_length,
        'featureTableBinaryByteLength': feature_table_binary_length,
        'batchTableJSONByteLength': batch_table_json_length,
        'batchTableBinaryByteLength': batch_table_binary_length,
    }


def parse_b3dm(data: bytes) -> dict:
    """
    Parst ein vollständiges b3dm File.

    Returns:
        Dict mit header, featureTable, batchTable und glTF-Daten
    """
    header = parse_b3dm_header(data)
    print(f"\n=== B3DM Header ===")
    print(f"Version: {header['version']}")
    print(f"Total size: {header['byteLength']:,} bytes")

    offset = 28  # Nach Header

    # Feature Table JSON
    feature_table = {}
    if header['featureTableJSONByteLength'] > 0:
        ft_json = data[offset:offset + header['featureTableJSONByteLength']]
        feature_table = json.loads(ft_json.decode('utf-8').rstrip('\x00'))
        print(f"\n=== Feature Table ===")
        print(json.dumps(feature_table, indent=2))
    offset += header['featureTableJSONByteLength']

    # Feature Table Binary (skip)
    offset += header['featureTableBinaryByteLength']

    # Batch Table JSON
    batch_table = {}
    if header['batchTableJSONByteLength'] > 0:
        bt_json = data[offset:offset + header['batchTableJSONByteLength']]
        batch_table = json.loads(bt_json.decode('utf-8').rstrip('\x00'))
        print(f"\n=== Batch Table ===")
        print(f"Keys: {list(batch_table.keys())}")

        # Zeige erste Einträge
        for key, value in batch_table.items():
            if isinstance(value, list) and len(value) > 0:
                print(f"  {key}: {value[:3]}... ({len(value)} entries)")
            else:
                print(f"  {key}: {value}")
    offset += header['batchTableJSONByteLength']

    # Batch Table Binary (skip)
    offset += header['batchTableBinaryByteLength']

    # glTF Daten
    gltf_data = data[offset:]
    print(f"\n=== glTF Data ===")
    print(f"Size: {len(gltf_data):,} bytes")

    # Prüfen ob glTF oder GLB
    if gltf_data[:4] == b'glTF':
        print("Format: GLB (binary glTF)")
        gltf_info = parse_glb(gltf_data)
    else:
        print("Format: Unknown")
        gltf_info = {}

    return {
        'header': header,
        'featureTable': feature_table,
        'batchTable': batch_table,
        'gltf': gltf_info
    }


def parse_glb(data: bytes) -> dict:
    """
    Parst GLB (binary glTF) Header und extrahiert Geometrie-Info.

    GLB Header (12 bytes):
    - magic (4 bytes): "glTF"
    - version (4 bytes): uint32
    - length (4 bytes): uint32
    """
    magic = data[0:4].decode('ascii')
    version = struct.unpack('<I', data[4:8])[0]
    length = struct.unpack('<I', data[8:12])[0]

    print(f"GLB Version: {version}")
    print(f"GLB Length: {length:,} bytes")

    # Chunks parsen
    offset = 12
    chunks = []

    while offset < len(data) - 8:
        chunk_length = struct.unpack('<I', data[offset:offset+4])[0]
        chunk_type = struct.unpack('<I', data[offset+4:offset+8])[0]
        chunk_data = data[offset+8:offset+8+chunk_length]

        chunk_type_str = {
            0x4E4F534A: 'JSON',  # "JSON"
            0x004E4942: 'BIN',   # "BIN\x00"
        }.get(chunk_type, f'0x{chunk_type:08X}')

        chunks.append({
            'type': chunk_type_str,
            'length': chunk_length,
            'data': chunk_data
        })

        print(f"  Chunk: {chunk_type_str}, {chunk_length:,} bytes")

        offset += 8 + chunk_length
        # Padding to 4-byte boundary
        if offset % 4 != 0:
            offset += 4 - (offset % 4)

    # JSON Chunk parsen
    gltf_json = None
    for chunk in chunks:
        if chunk['type'] == 'JSON':
            gltf_json = json.loads(chunk['data'].decode('utf-8'))
            break

    if gltf_json:
        print(f"\n=== glTF JSON ===")

        # Meshes
        meshes = gltf_json.get('meshes', [])
        print(f"Meshes: {len(meshes)}")

        # Accessors (enthalten min/max für Vertices)
        accessors = gltf_json.get('accessors', [])
        print(f"Accessors: {len(accessors)}")

        # Finde Position Accessor
        for i, accessor in enumerate(accessors):
            if accessor.get('type') == 'VEC3':
                min_vals = accessor.get('min', [])
                max_vals = accessor.get('max', [])
                if min_vals and max_vals:
                    print(f"\n  Accessor {i} (VEC3):")
                    print(f"    Min: {min_vals}")
                    print(f"    Max: {max_vals}")
                    if len(min_vals) == 3 and len(max_vals) == 3:
                        print(f"    Height range: {min_vals[2]:.2f} to {max_vals[2]:.2f}")
                        print(f"    Building height: {max_vals[2] - min_vals[2]:.2f}m")

    return {
        'version': version,
        'chunks': len(chunks),
        'json': gltf_json
    }


def main():
    """Hauptfunktion - lädt und analysiert ein Test-Tile."""

    # Test mit Tiles aus verschiedenen Regionen
    # Berechnet aus Slippy Map Koordinaten bei Zoom 11
    test_tiles = [
        "11/1066/720.b3dm",  # Bern (46.95, 7.45)
        "11/1067/720.b3dm",  # Bern Ost
        "11/1066/719.b3dm",  # Bern Nord
        "11/1068/722.b3dm",  # Thun
        "11/1891/425.b3dm",  # Tessin (Original)
    ]

    for tile_path in test_tiles:
        print(f"\n{'='*60}")
        print(f"Testing tile: {tile_path}")
        print('='*60)

        try:
            data = download_tile(tile_path)
            result = parse_b3dm(data)

            # Zusammenfassung
            print(f"\n=== SUMMARY ===")
            batch_length = result['featureTable'].get('BATCH_LENGTH', 0)
            print(f"Buildings in tile: {batch_length}")

            if 'EGID' in result.get('batchTable', {}):
                egids = result['batchTable']['EGID']
                print(f"EGIDs: {egids[:5]}...")

            print("\nTile successfully parsed!")
            break

        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == '__main__':
    main()
