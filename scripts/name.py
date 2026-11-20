"""Generate the twoonemoon SVG animation. Python stdlib; no runtime dependencies.

The custom monoline lettering is sampled by arc length. Its Fourier series drives
an XY plotter: two coordinate carriages and a pen. No rotating circles.
Run: python scripts/name.py [output-assets-directory]
"""
from pathlib import Path
import bisect
import cmath
import math
import sys

TAU=2*math.pi
N=2600
K=96
PERIOD=20
DRAW=10

def bezier(points, count=45):
    n=len(points)-1
    return [sum(math.comb(n,j)*(1-t)**(n-j)*t**j*p for j,p in enumerate(points)) for t in (i/count for i in range(count+1))]

def letter(char):
    p=lambda x,y:complex(x,y)
    if char=='t':
        return 58,[bezier([p(31,78),p(20,168),p(13,218),p(54,203)]),bezier([p(0,128),p(26,125),p(57,125)])]
    if char=='w':
        return 104,[bezier([p(2,131),p(8,173),p(14,210),p(29,209)])+bezier([p(29,209),p(40,204),p(51,153),p(52,140)])[1:]+bezier([p(52,140),p(56,174),p(59,212),p(73,208)])[1:]+bezier([p(73,208),p(88,204),p(100,163),p(103,131)])[1:]]
    if char=='o':
        return 75,[[p(37+34*math.cos(a),170+40*math.sin(a)) for a in (-1.1-TAU*i/100 for i in range(101))]]
    if char=='n':
        return 84,[[p(4,210),p(8,132)]+bezier([p(8,186),p(16,118),p(78,101),p(77,158)])[1:]+bezier([p(77,158),p(76,179),p(74,198),p(78,210)])[1:]]
    if char=='e':
        return 75,[bezier([p(6,173),p(33,175),p(70,156),p(63,140)])+bezier([p(63,140),p(53,115),p(1,127),p(3,176)])[1:]+bezier([p(3,176),p(5,213),p(46,223),p(71,195)])[1:]]
    if char=='m':
        return 125,[[p(4,210),p(7,132)]+bezier([p(7,181),p(18,118),p(63,114),p(60,161)])[1:]+[p(58,209),p(61,164)]+bezier([p(61,164),p(74,118),p(120,117),p(118,161)])[1:]+[p(116,210)]]
    raise ValueError(char)

def prepare():
    strokes=[]
    x=42
    for char in 'twoonemoon':
        width,paths=letter(char)
        strokes.extend([[z+x for z in path] for path in paths])
        x+=width+17
    scale=1116/(x-59)
    strokes=[[complex((z.real-42)*scale+42,(z.imag-145)*scale+145) for z in path] for path in strokes]
    segments=[]
    for i,path in enumerate(strokes):
        if i:segments.append((strokes[i-1][-1],path[0],False))
        segments.extend((a,b,True) for a,b in zip(path,path[1:]) if abs(b-a)>1e-8)
    segments.append((strokes[-1][-1],strokes[0][0],False))
    ends=[];total=0
    for a,b,_ in segments:
        total+=abs(b-a);ends.append(total)
    samples=[];down=[]
    for i in range(N):
        at=i/N*total
        j=min(bisect.bisect_right(ends,at),len(segments)-1)
        a,b,ink=segments[j]
        start=ends[j-1] if j else 0
        samples.append(a+(b-a)*(at-start)/(ends[j]-start))
        down.append(ink)
    terms=[]
    for k in range(-K,K+1):
        coef=sum(z*cmath.exp(-1j*TAU*k*i/N) for i,z in enumerate(samples))/N
        terms.append((k,coef))
    reconstructed=[sum(c*cmath.exp(1j*TAU*k*i/N) for k,c in terms) for i in range(N)]
    # This bounds the visible lettering error, including retraced vertical stems.
    rms=math.sqrt(sum(abs(a-b)**2 for a,b,d in zip(samples,reconstructed,down) if d)/sum(down))
    assert rms<2, rms
    return terms,reconstructed,down,rms

def render(terms,points,down,theme,animated=True):
    bg,grid,major,pen,circle=({'light':('#f8f9fa','#e7e9ed','#d4d9df','#b83425','#668782'),'dark':('#0e1116','#1a2029','#29313d','#f17b65','#6eaaa5')}[theme])
    fmt=lambda n:f'{n:.2f}'
    paths=[];i=0
    while i<N:
        if not down[i]:i+=1;continue
        start=i
        while i+1<N and down[i+1]:i+=1
        end=i
        coords='M'+' L'.join(f'{fmt(z.real)} {fmt(z.imag)}' for z in points[start:end+1])
        paths.append((start/N,end/N,coords));i+=1
    css=[];ink=[]
    for i,(start,end,d) in enumerate(paths):
        a=start*DRAW/PERIOD*100;b=end*DRAW/PERIOD*100
        css.append(f'.stroke-{i}{{animation:stroke-{i} {PERIOD}s linear infinite}}@keyframes stroke-{i}{{0%,{a:.4f}%{{stroke-dashoffset:1;opacity:1}}{b:.4f}%,87%{{stroke-dashoffset:0;opacity:1}}98%,100%{{stroke-dashoffset:0;opacity:0}}}}')
        ink.append(f'<path class="stroke-{i}" pathLength="1" stroke-dasharray="1" d="{d}"/>')
    # The animation has only three translating groups, with the same time base.
    # All positions come from the Fourier reconstruction used for the ink.
    frames=points[::4]+[points[0]]
    x_values=';'.join(f'{fmt(z.real)} 40' for z in frames)
    y_values=';'.join(f'23 {fmt(z.imag)}' for z in frames)
    pen_values=';'.join(f'{fmt(z.real)} {fmt(z.imag)}' for z in frames)
    def move(values):
        return f'<animateTransform attributeName="transform" type="translate" values="{values}" dur="{DRAW}s" repeatCount="indefinite"/>'
    plotter=f'''<g class="mechanism">
<g>{move(x_values)}<path class="guide" d="M0 7V220"/><rect class="slider" x="-5" y="-5" width="10" height="10"/></g>
<g>{move(y_values)}<path class="guide" d="M7 0H1150"/><rect class="slider" x="-5" y="-5" width="10" height="10"/></g>
<g class="pen">{move(pen_values)}<path d="M-8 0H8M0-8V8"/><rect x="-2.5" y="-2.5" width="5" height="5"/></g></g>'''
    waves=[]
    for channel,offset in [('X',70),('Y',690)]:
        component=[z.real if channel=='X' else z.imag for z in frames]
        low=min(component);high=max(component)
        coords='M'+' L'.join(f'{fmt(offset+i/(len(component)-1)*440)} {fmt(314-34*(value-low)/(high-low))}' for i,value in enumerate(component))
        waves.append(f'<path class="wave" d="{coords}"/><text x="{offset}" y="338">{channel}(t)</text><g class="wave-cursor"><animateTransform attributeName="transform" type="translate" from="{offset} 0" to="{offset+440} 0" dur="{DRAW}s" repeatCount="indefinite"/><path d="M0 276V319"/></g>')
    style=f'''.ink path{{fill:none;stroke:{pen};stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}}
{''.join(css)}
.mechanism,.wave-cursor{{animation:plotter {PERIOD}s linear infinite}}
.guide{{fill:none;stroke:{circle};stroke-width:1;stroke-dasharray:3 5;opacity:.7}}
.slider{{fill:{bg};stroke:{circle};stroke-width:1.4}}.pen{{fill:{pen};stroke:{pen};stroke-width:1.3}}
.rails,.wave{{fill:none;stroke:{circle};stroke-width:1;opacity:.5}}.wave{{opacity:.75}}
.wave-cursor{{stroke:{pen};stroke-width:1}}text{{fill:{circle};font:14px Consolas,monospace;letter-spacing:1px}}
@keyframes plotter{{0%{{opacity:0}}2%,50%{{opacity:1}}55%,100%{{opacity:0}}}}
@media(prefers-reduced-motion:reduce){{.ink path{{animation:none;stroke-dashoffset:0;opacity:1}}.mechanism,.wave-cursor{{display:none}}}}'''
    if not animated:style+='\n.ink path{animation:none;stroke-dashoffset:0;opacity:1}.mechanism,.wave-cursor{display:none}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="355" viewBox="0 0 1200 355" role="img" aria-label="twoonemoon">
<title>twoonemoon</title><desc>An XY plotter draws the nickname. The two graphs show the pen coordinates over time.</desc>
<defs><pattern id="squares" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="{grid}"/></pattern><pattern id="paper" width="125" height="125" patternUnits="userSpaceOnUse"><rect width="125" height="125" fill="url(#squares)"/><path d="M125 0H0V125" fill="none" stroke="{major}"/></pattern><clipPath id="bounds"><rect width="1200" height="355" rx="8"/></clipPath></defs>
<style>{style}</style><g clip-path="url(#bounds)"><rect width="1200" height="355" fill="{bg}"/><rect width="1200" height="355" fill="url(#paper)"/><path class="rails" d="M42 40H1170M23 65V245M42 262H1170"/><g class="ink">{''.join(ink)}</g>{plotter}<g>{''.join(waves)}</g></g></svg>'''

if __name__=='__main__':
    output=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'assets'
    output.mkdir(parents=True,exist_ok=True)
    terms,points,down,rms=prepare()
    for theme in ['light','dark']:
        (output/f'name-{theme}.svg').write_text(render(terms,points,down,theme),encoding='utf-8')
    # Useful for inspecting the completed word without waiting for an animation.
    if '--check' in sys.argv:
        (output/'name-check.svg').write_text(render(terms,points,down,'light',False),encoding='utf-8')
    print(f'Generated twoonemoon animation; {len(terms)} Fourier terms; lettering RMS error {rms:.3f}px.')
