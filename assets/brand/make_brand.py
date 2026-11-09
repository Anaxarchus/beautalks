from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
F='/usr/share/fonts/opentype/inter/Inter-%s.otf'
fonts={w:TTFont(F%w) for w in ('ExtraLight','SemiBold','Regular','Bold')}

def run(text, weight, size, x, y, spacing=0.0):
    f=fonts[weight]; gs=f.getGlyphSet(); cmap=f.getBestCmap(); upm=f['head'].unitsPerEm
    s=size/upm; d=[]
    for ch in text:
        g=cmap.get(ord(ch))
        if g is None: continue
        pen=SVGPathPen(gs); tp=TransformPen(pen,(s,0,0,-s,x,y))
        gs[g].draw(tp); d.append(pen.getCommands())
        x+=gs[g].width*s+spacing
    return ' '.join(d), x

WAVE='M{x0} {y} q10 -14 20 0 t20 0 t20 0 t20 0 q10 -8 20 0 t20 0 q10 -4 20 0 t20 0 L{x1} {y}'
def logo(theme, tagline=True):
    ink,accent,line,sub = {'light':('#2b2233','#7a3e8e','#e07a5f','#8f839a'),
                           'dark':('#f1ecf4','#c993dc','#ee8f74','#a99bb6')}[theme]
    d1,x=run('beau','ExtraLight',92,20,98)
    d2,x2=run('talks','SemiBold',92,x,98)
    W=int(max(x2,520))+28
    parts=[f'<path d="{d1}" fill="{ink}"/>',f'<path d="{d2}" fill="{accent}"/>',
           f'<path d="{WAVE.format(x0=24,y=128,x1=int(x2)-4)}" fill="none" stroke="{line}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>']
    H=146
    if tagline:
        d3,x3=run('SMOOTHS OUT THE WRINKLES IN RADIO PROGRAMMING','Regular',15,24,160,3.0)
        parts.append(f'<path d="{d3}" fill="{sub}"/>'); W=int(max(W,x3+24)); H=176
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="beautalks">'+''.join(parts)+'</svg>'

def icon():
    d,x=run('b','Bold',300,0,0)
    # centre the glyph: measure via bounds pen
    from fontTools.pens.boundsPen import BoundsPen
    f=fonts['Bold']; gs=f.getGlyphSet(); g=f.getBestCmap()[ord('b')]; bp=BoundsPen(gs); gs[g].draw(bp)
    xmin,ymin,xmax,ymax=bp.bounds; s=300/f['head'].unitsPerEm
    w=(xmax-xmin)*s; h=(ymax-ymin)*s
    ox=(512-w)/2 - xmin*s; base=(512+h)/2 - 40 + ymin*s
    d,_=run('b','Bold',300,ox,base)
    wave='M136 408 q12 -18 24 0 t24 0 t24 0 q12 -10 24 0 t24 0 q12 -5 24 0 L376 408'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="beautalks">'
            '<rect width="512" height="512" rx="112" fill="#7a3e8e"/>'
            f'<path d="{d}" fill="#ffffff"/>'
            f'<path d="{wave}" fill="none" stroke="#ee8f74" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/></svg>')

open('brand/beautalks-logo.svg','w').write(logo('light'))
open('brand/beautalks-logo-dark.svg','w').write(logo('dark'))
open('brand/beautalks-wordmark.svg','w').write(logo('light',False))
open('brand/beautalks-wordmark-dark.svg','w').write(logo('dark',False))
open('brand/beautalks-icon.svg','w').write(icon())
