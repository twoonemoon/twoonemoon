"""Build the calligraphic nickname artwork from shaped, licensed font outlines.

Build dependencies: fonttools, uharfbuzz. Output SVG has no external dependencies.
"""
from pathlib import Path
import bisect
import cmath
import math
import sys
import json
import argparse
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE=Path(__file__).resolve().parent
W,H=1600,560
PERIOD=48
N=112

def z(point):return complex(*point)
def f(value):return f'{value:.2f}'.rstrip('0').rstrip('.')

class Flatten(BasePen):
    def __init__(self,glyphs):
        super().__init__(glyphs);self.contours=[];self.current=[]
    def _moveTo(self,p):self.current=[z(p)]
    def _lineTo(self,p):self.current.append(z(p))
    def _curveToOne(self,a,b,c):
        start=z(self._getCurrentPoint());a,b,c=map(z,(a,b,c))
        steps=max(6,int((abs(a-start)+abs(b-a)+abs(c-b))/8))
        self.current.extend((1-t)**3*start+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*c for t in (i/steps for i in range(1,steps+1)))
    def _qCurveToOne(self,a,b):
        start=z(self._getCurrentPoint());a,b=map(z,(a,b))
        steps=max(5,int((abs(a-start)+abs(b-a))/8))
        self.current.extend((1-t)**2*start+2*(1-t)*t*a+t*t*b for t in (i/steps for i in range(1,steps+1)))
    def _closePath(self):
        if abs(self.current[-1]-self.current[0])>1e-8:self.current.append(self.current[0])
        self.contours.append(self.current);self.current=[]
    def _endPath(self):self._closePath()

def lettering():
    filename=HERE/'fonts'/'GreatVibes-Regular.ttf'
    data=filename.read_bytes()
    font=TTFont(filename);glyphs=font.getGlyphSet()
    hfont=hb.Font(hb.Face(data));hfont.scale=(font['head'].unitsPerEm,)*2
    buf=hb.Buffer();buf.add_str('twoonemoon');buf.guess_segment_properties()
    hb.shape(hfont,buf,{'kern':True,'liga':True,'calt':True})
    items=[];x=y=0;bounds=BoundsPen(glyphs)
    for info,pos in zip(buf.glyph_infos,buf.glyph_positions):
        glyph=glyphs[font.getGlyphName(info.codepoint)]
        gx,gy=x+pos.x_offset,y+pos.y_offset
        glyph.draw(TransformPen(bounds,(1,0,0,1,gx,gy)))
        items.append((glyph,gx,gy,info.cluster))
        x+=pos.x_advance;y+=pos.y_advance
    left,bottom,right,top=bounds.bounds
    scale=min(1390/(right-left),310/(top-bottom))
    ox=W/2-scale*(left+right)/2
    oy=258+scale*(bottom+top)/2
    letters=[];contours=[]
    for glyph,gx,gy,cluster in items:
        pen=SVGPathPen(glyphs)
        matrix=(scale,0,0,-scale,ox+scale*gx,oy-scale*gy)
        glyph.draw(TransformPen(pen,matrix))
        letters.append({'d':pen.getCommands(),'cluster':cluster})
        flat=Flatten(glyphs);glyph.draw(flat)
        for shape in flat.contours:
            points=[complex(ox+scale*(gx+p.real),oy-scale*(gy+p.imag)) for p in shape]
            if sum(abs(b-a) for a,b in zip(points,points[1:]))>10:
                contours.append((cluster,points))
    assert len(buf.glyph_infos)==len(items) and all(info.codepoint for info in buf.glyph_infos)
    return letters,contours

def sample(points,count=N):
    lengths=[0]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+abs(b-a))
    out=[]
    for i in range(count):
        distance=lengths[-1]*i/count
        k=min(bisect.bisect_right(lengths,distance)-1,len(points)-2)
        a,b=points[k:k+2];den=lengths[k+1]-lengths[k]
        out.append(a+(b-a)*(distance-lengths[k])/den if den else a)
    return out

def spline(points):
    # Periodic Catmull-Rom converted exactly to cubic Bezier segments.
    path=f'M{f(points[0].real)} {f(points[0].imag)}'
    for i,a in enumerate(points):
        before=points[(i-1)%len(points)];b=points[(i+1)%len(points)];after=points[(i+2)%len(points)]
        c=a+(b-before)/6;d=b-(after-a)/6
        path+=f'C{f(c.real)} {f(c.imag)} {f(d.real)} {f(d.imag)} {f(b.real)} {f(b.imag)}'
    return path+'Z'

def deform(points,strength,phase,layer):
    out=[]
    for j,p in enumerate(points):
        u=j/len(points)
        envelope=cmath.exp(1j*(2*math.pi*u+phase))+.31*cmath.exp(-1j*(6*math.pi*u-phase*2))+.13*cmath.exp(1j*(10*math.pi*u+phase))
        flow=complex(1.1*envelope.real,.7*envelope.imag)
        tilt=complex((p.real-W/2)*.1,0)
        out.append(p+strength*(flow+tilt/60)+layer*strength*.13*cmath.exp(1j*(4*math.pi*u+phase)))
    return out

def svg(theme,letters,contours,still=False):
    dark=theme=='dark'
    bg='#0e1116' if dark else '#f8f9fa'
    ink='#f2e6dc' if dark else '#25282e'
    coral='#f17b65' if dark else '#b83425'
    muted='#716663' if dark else '#a29a95'
    low='#342a28' if dark else '#e2d9d5'
    defs=f'''<linearGradient id="ink" gradientUnits="userSpaceOnUse" x1="100" y1="180" x2="1500" y2="350"><stop stop-color="{ink}"/><stop offset=".5" stop-color="{ink}"/><stop offset=".84" stop-color="{coral}"/><stop offset="1" stop-color="{ink}"/></linearGradient><linearGradient id="copper"><stop stop-color="{coral}" stop-opacity=".1"/><stop offset=".5" stop-color="{coral}"/><stop offset="1" stop-color="{ink}" stop-opacity=".6"/></linearGradient><radialGradient id="aura"><stop stop-color="{coral}" stop-opacity=".055"/><stop offset="1" stop-color="{bg}" stop-opacity="0"/></radialGradient><clipPath id="frame"><rect width="{W}" height="{H}" rx="10"/></clipPath>'''
    styles=f'''svg{{background:{bg}}}.ribbon{{fill:none;stroke-linecap:round;stroke-linejoin:round}}.wire{{fill:none;stroke:{muted};stroke-width:.8}}.letter{{fill:url(#ink)}}.reduced{{display:none}}.ghost{{fill:{ink};opacity:.035}}.field{{fill:none;stroke:{low};stroke-width:.8}}.ornament{{fill:none;stroke:url(#copper);stroke-linecap:round}}'''
    layers=[]
    # The same smooth homotopy is used by all ribbons. At strength=0 their
    # geometry is exactly the sampled font outline; no random simulation.
    key_times='0;.10;.26;.44;.60;.86;.94;1'
    strengths=[200,150,85,20,0,0,60,200]
    phases=[0,.8,1.8,2.6,3.4,3.4,4.8,2*math.pi]
    # Equal endpoints make the loop continuous, including the deformation phase.
    for index,(cluster,raw) in enumerate(contours):
        points=sample(raw)
        for layer in range(3):
            values=[spline(deform(points,a,phase+index*.37,layer-1)) for a,phase in zip(strengths,phases)]
            color=[coral,ink,muted][layer]
            start=3.0+cluster*.73
            end=21+cluster*.4
            classname=f'r{index}_{layer}'
            styles+=f'.{classname}{{animation:{classname} {PERIOD}s linear infinite}}@keyframes {classname}{{0%,{start/PERIOD*100:.3f}%{{opacity:0;stroke-dashoffset:1}}{(start+4)/PERIOD*100:.3f}%{{opacity:{[.55,.65,.3][layer]}}}{end/PERIOD*100:.3f}%{{stroke-dashoffset:0;opacity:{[.65,.8,.3][layer]}}}68%{{opacity:{[.25,.5,.14][layer]}}}86%{{opacity:0}}100%{{opacity:0;stroke-dashoffset:0}}}}'
            animate=f'<animate attributeName="d" dur="{PERIOD}s" repeatCount="indefinite" values="{";".join(values)}" keyTimes="{key_times}" calcMode="spline" keySplines="'+ ';'.join(['.42 0 .58 1']*7)+'"/>'
            layers.append(f'<path class="ribbon {classname}" stroke="{color}" stroke-width="{[1.0,.65,.45][layer]}" pathLength="1" stroke-dasharray="1" d="{values[0]}">{animate}</path>')
    fills=[]
    for i,item in enumerate(letters):
        a=(17+i*.95)/PERIOD*100;b=(24+i*.7)/PERIOD*100
        styles+=f'.l{i}{{animation:l{i} {PERIOD}s ease-in-out infinite}}@keyframes l{i}{{0%,{a:.3f}%{{opacity:0}}{b:.3f}%,87%{{opacity:1}}98%,100%{{opacity:0}}}}'
        fills.append(f'<path class="letter l{i}" d="{item["d"]}"/>')
    field=[]
    for row in range(22):
        paths=[]
        for phase in [0,math.pi/2,math.pi,3*math.pi/2,2*math.pi]:
            coords=[]
            for i in range(81):
                x=20+i*19.5
                envelope=math.exp(-((x-W/2)/570)**2)
                y=455+row*3.2+envelope*(12*math.sin(x/150+phase+row*.14)+9*math.sin(x/83-phase))
                coords.append(complex(x,y))
            paths.append('M'+'L'.join(f'{f(p.real)} {f(p.imag)}' for p in coords))
        field.append(f'<path d="{paths[0]}"><animate attributeName="d" dur="{PERIOD}s" values="{";".join(paths)}" keyTimes="0;.25;.5;.75;1" calcMode="spline" keySplines=".37 0 .63 1;.37 0 .63 1;.37 0 .63 1;.37 0 .63 1" repeatCount="indefinite"/></path>')
    # Two long cubic flourishes echo the calligraphic nib rather than machinery.
    ornament='<path d="M110 397C270 452 391 426 549 402S875 366 1060 397S1340 440 1490 385"/><path d="M185 113C428 42 566 83 760 104S1152 134 1410 77"/>'
    styles+=f'.ornament{{stroke-width:1.05;animation:flourish {PERIOD}s ease-in-out infinite;stroke-dasharray:1}}@keyframes flourish{{0%,14%{{stroke-dashoffset:1;opacity:0}}31%{{opacity:.5}}60%,83%{{stroke-dashoffset:0;opacity:.7}}98%,100%{{stroke-dashoffset:0;opacity:0}}}}'
    ornament=ornament.replace('<path ','<path pathLength="1" ')
    native=''.join(f'<path d="{item["d"]}"/>' for item in letters)
    if still:
        styles+='.animated,.ghost{display:none}.reduced{display:block;fill:url(#ink)}'
    styles+='@media(prefers-reduced-motion:reduce){.animated,.ghost{display:none!important}.reduced{display:block;fill:url(#ink)}}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="twoonemoon"><title>twoonemoon</title><desc>Calligraphy shaped from Great Vibes. Three layers of periodic Bezier ribbons converge to the exact letter outlines over a 48 second cycle.</desc><defs>{defs}</defs><style>{styles}</style><g clip-path="url(#frame)"><rect width="{W}" height="{H}" fill="{bg}"/><rect width="{W}" height="{H}" fill="url(#aura)"/><g class="ghost">{native}</g><g class="animated"><g class="field">{''.join(field)}</g><g class="ornament">{ornament}</g>{''.join(layers)}{''.join(fills)}</g><g class="reduced">{native}</g></g></svg>'''

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=HERE.parent/'assets')
    parser.add_argument('--proofs',action='store_true')
    args=parser.parse_args()
    letters,contours=lettering()
    output=args.output
    output.mkdir(parents=True,exist_ok=True)
    for theme in ['light','dark']:
        (output/f'name-calligraphy-{theme}.svg').write_text(svg(theme,letters,contours),encoding='utf-8')
        if args.proofs:(output/f'calligraphy-proof-{theme}.svg').write_text(svg(theme,letters,contours,True),encoding='utf-8')
    print(json.dumps({'glyphs':len(letters),'contours':len(contours),'period':PERIOD,'files':[(p.name,p.stat().st_size) for p in output.glob('*calligraphy*.svg')]}))
