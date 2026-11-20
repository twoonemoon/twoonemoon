"""Geometry and asset check: python scripts/check_name.py."""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import name as artwork

letters,contours=artwork.lettering()
for _,raw in contours:
    points=artwork.sample(raw)
    assert artwork.deform(points,0,.8,1)==points
    start=artwork.deform(points,200,0,1)
    end=artwork.deform(points,200,2*math.pi,1)
    assert max(abs(a-b) for a,b in zip(start,end))<1e-8
    assert all(0<p.real<artwork.W and 0<p.imag<artwork.H for p in points)
for theme in ['light','dark']:
    svg=ET.parse(Path(__file__).resolve().parents[1]/'assets'/f'name-calligraphy-{theme}.svg')
    for move in svg.findall('.//{http://www.w3.org/2000/svg}animate'):
        values=move.get('values').split(';')
        assert values[0]==values[-1]
        assert len(values)==len(move.get('keyTimes').split(';'))
        assert move.get('dur')=='48s'
        assert move.get('calcMode')=='spline'
print('PASS: font bounds, exact convergence, periodic geometry and smooth animation timing.')
