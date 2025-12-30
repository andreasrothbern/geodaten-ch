#!/usr/bin/env python3
import argparse, sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Generator, Tuple, Optional, Dict

script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.services.height_db import (
    init_database, bulk_insert_heights, bulk_insert_heights_detailed,
    log_import, get_database_stats
)

def parse_citygml(file_path):
    print(f'Parsing CityGML: {file_path.name}')
    ns = {'gen': 'http://www.opengis.net/citygml/generics/2.0'}
    ctx = ET.iterparse(str(file_path), events=('end',))
    count = detailed_count = 0
    
    for _, elem in ctx:
        if elem.tag.endswith('}Building'):
            egid = dach_max = dach_min = terrain = None
            for attr in elem.findall('.//gen:intAttribute', ns):
                if attr.get('name') == 'EGID':
                    v = attr.find('gen:value', ns)
                    if v is not None and v.text:
                        try: egid = int(v.text)
                        except: pass
            for attr in elem.findall('.//gen:doubleAttribute', ns):
                name = attr.get('name', '')
                v = attr.find('gen:value', ns)
                if v is not None and v.text:
                    try:
                        val = float(v.text)
                        if name == 'DACH_MAX': dach_max = val
                        elif name == 'DACH_MIN': dach_min = val
                        elif name == 'GELAENDEPUNKT': terrain = val
                    except: pass
            if egid and dach_max and terrain:
                h = dach_max - terrain
                if h > 0:
                    count += 1
                    if count % 1000 == 0: print(f'  {count}...')
                    trauf = round(dach_min - terrain, 2) if dach_min else None
                    det = {'egid': egid, 'traufhoehe_m': trauf, 'firsthoehe_m': round(h, 2),
                           'gebaeudehoehe_m': round(h, 2), 'terrain_m': round(terrain, 2),
                           'dach_max_m': round(dach_max, 2), 'dach_min_m': round(dach_min, 2) if dach_min else None}
                    if trauf: detailed_count += 1
                    yield (egid, round(h, 2), det)
            elem.clear()
    print(f'  {count} Gebaeude, {detailed_count} mit Trauf')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('input_file', type=Path)
    p.add_argument('--canton', default='CH')
    p.add_argument('--version', default='3.0')
    p.add_argument('--batch-size', type=int, default=5000)
    args = p.parse_args()
    init_database()
    src = f'swissBUILDINGS3D_{args.version}_{args.canton}'
    bl, bd = [], []
    total = det = 0
    for e, h, d in parse_citygml(args.input_file):
        bl.append((e, h))
        if d: bd.append(d)
        if len(bl) >= args.batch_size:
            bulk_insert_heights(bl, src)
            if bd: bulk_insert_heights_detailed(bd, src); det += len(bd)
            total += len(bl)
            print(f'  {total:,} importiert')
            bl, bd = [], []
    if bl: bulk_insert_heights(bl, src); total += len(bl)
    if bd: bulk_insert_heights_detailed(bd, src); det += len(bd)
    log_import(args.input_file.name, args.canton, total, args.version)
    print(f'OK: {total:,} Gebaeude, {det:,} mit Trauf/First')

if __name__ == '__main__': main()
