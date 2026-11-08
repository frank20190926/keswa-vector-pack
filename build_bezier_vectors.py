#!/usr/bin/env python3
"""Reproducible KESWA vector exports. No external downloads or Adobe dependency."""
from pathlib import Path
import json, re, math, zipfile, hashlib
import numpy as np
import fitz
import ezdxf
from PIL import Image
from bezier_geometry import build_components
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'exports'
W,H=Image.open(ROOT/'assets/source-light.png').size
PALETTE=['#e46a35','#f0b735','#62b68a','#3cb8cb','#7a93ff','#ca80e8','#ff7ea5']

def parse(d):
    tok=re.findall(r'[MLCZmlcz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',d)
    i=0; out=[]
    while i<len(tok):
        op=tok[i];i+=1;n={'M':2,'L':2,'C':6,'Z':0}[op]
        out.append((op,[float(t) for t in tok[i:i+n]]));i+=n
    return out

def enrich(c):
    ops=parse(c['d']); anchors=[];handles=[];p=None;start=None; extrema=[]
    for op,v in ops:
        if op=='M':p=v;start=v;anchors.append(v);extrema.append(v)
        elif op=='L':p=v;anchors.append(v);extrema.append(v)
        elif op=='C':
            a=np.array(p);b=np.array(v[:2]);cc=np.array(v[2:4]);e=np.array(v[4:]);
            handles.extend([{'anchor':p,'control':v[:2]},{'anchor':v[4:],'control':v[2:4]}]);anchors.append(v[4:]);extrema.append(v[4:])
            for axis in range(2):
                coeff=[-a[axis]+3*b[axis]-3*cc[axis]+e[axis],2*(a[axis]-2*b[axis]+cc[axis]),b[axis]-a[axis]]
                for t in np.roots(np.trim_zeros(coeff,'f')):
                    if np.isreal(t) and 0<float(t)<1:
                        t=float(t);extrema.append(((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*cc+t**3*e).tolist())
            p=v[4:]
        else:p=start
    # Closing endpoint identical to a subpath start is one anchor, not two.
    unique=list(dict.fromkeys(tuple(a) for a in anchors))
    a=np.array(extrema);lo=a.min(axis=0);hi=a.max(axis=0)
    c.update(bbox=[round(float(x),4) for x in [*lo,*(hi-lo)]],nodes=len(unique),anchor_count=len(unique),anchors=[list(a) for a in unique],handles=handles,cubic_segments=sum(op=='C' for op,v in ops),line_segments=sum(op=='L' for op,v in ops))
    c.pop('polys',None)
    return c

def rgb(col):return tuple(int(col[i:i+2],16)/255 for i in (1,3,5))
def svg(cs,dark=False,box=None,bg=None,blueprint=False):
    box=box or [0,0,W,H]
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" viewBox="{" ".join(map(str,box))}">']
    # Official Inkscape namespace.
    s[0]=s[0].replace('http://www.inkscape.org/namespaces/inkscape','http://www.inkscape.org/namespaces/inkscape')
    if bg:s.append(f'<rect x="{box[0]}" y="{box[1]}" width="{box[2]}" height="{box[3]}" fill="{bg}"/>')
    for i,c in enumerate(cs):
        col=c['color_dark' if dark else 'color_light'];ident=c['id']
        s.append(f'<g id="{ident}" inkscape:groupmode="layer" inkscape:label="{ident}" data-layer-name="{ident}"><title>{ident}</title><path fill="{col}" fill-rule="evenodd" d="{c["d"]}"/></g>')
    return ''.join(s)+'</svg>'

def draw(page,c,oc=0,stroke=False,transform=None,color=None):
    def point(v):
        x,y=v
        if transform:x,y=transform(x,y)
        return fitz.Point(x,y)
    sh=page.new_shape();p=start=None
    for op,v in parse(c['d']):
        if op=='M':p=point(v);start=p
        elif op=='L':q=point(v);sh.draw_line(p,q);p=q
        elif op=='C':q=point(v[4:]);sh.draw_bezier(p,point(v[:2]),point(v[2:4]),q);p=q
        elif op=='Z':
            if abs(p-start)>1e-8:sh.draw_line(p,start)
            p=start
    col=rgb(color or c['color_light'])
    sh.finish(color=col if stroke else None,fill=None if stroke else col,width=1 if stroke else 0,even_odd=True,closePath=False,oc=oc)
    sh.commit()

def png(cs,path,width=3840,dark=False,box=None):
    box=box or [0,0,W,H];x,y,w,h=box
    doc=fitz.open();p=doc.new_page(width=w,height=h)
    for c in cs:draw(p,c,transform=lambda a,b:(a-x,b-y),color=c['color_dark' if dark else 'color_light'])
    p.get_pixmap(matrix=fitz.Matrix(width/w,width/w),alpha=True).save(path)
    doc.close()

def ps(cs,ai=False):
    s=['%!PS-Adobe-3.0 EPSF-3.0',f'%%BoundingBox: 0 0 {W} {H}',f'%%HiResBoundingBox: 0 0 {W} {H}','%%LanguageLevel: 3','%%Creator: KESWA Bezier Vector Builder','%%Title: KESWA - 17 named component layers','%%DocumentData: Clean7Bit','%%Pages: 1']
    if ai:s+=['%AI3_ColorUsage: Color','%AI3_TemplateBox: 0 0 2172 724','%AI5_FileFormat 3.0','%AI3_DocumentPreview: None']
    s+=['%%EndComments','%%BeginProlog','/m {moveto} bind def /l {lineto} bind def /c {curveto} bind def','/h {closepath} bind def /f {eofill} bind def','/Xa {setrgbcolor} bind def','/Lb {10 {pop} repeat} bind def /Ln {pop} bind def /LB {} bind def','/*u {} bind def /*U {} bind def','%%EndProlog','%%Page: 1 1']
    for c in cs:
        s+=['%AI5_BeginLayer','1 1 1 1 0 0 0 0 0 0 Lb',f'({c["id"]}) Ln',f'%%BeginObject: {c["id"]}','*u', ' '.join(f'{v:.6f}' for v in rgb(c['color_light']))+' Xa','newpath']
        for op,v in parse(c['d']):
            a=[v[i] if i%2==0 else H-v[i] for i in range(len(v))]
            s.append(' '.join(f'{v:.4f}' for v in a)+{'M':' m','L':' l','C':' c','Z':'h'}[op])
        s+=['f','*U','%%EndObject','LB','%AI5_EndLayer']
    s+=['showpage','%%Trailer','%%EOF']
    return '\n'.join(s)+'\n'

def pdf(cs):
    doc=fitz.open();ocgs={c['id']:doc.add_ocg(c['id']) for c in cs}
    for dark in [False,True]:
        p=doc.new_page(width=W,height=H)
        if dark:p.draw_rect(p.rect,fill=rgb('#141a22'),color=None,overlay=False)
        for c in cs:draw(p,c,ocgs[c['id']],color=c['color_dark' if dark else 'color_light'])
    p=doc.new_page(width=W,height=H)
    p.draw_rect(p.rect,fill=rgb('#0b2036'),color=None)
    p.insert_text((48,48),'KESWA / EXPLODED 17-LAYER CAD & BEZIER NODE BLUEPRINT',fontsize=25,color=(1,1,1))
    p.insert_text((48,73),'Square anchors / magenta outgoing handles / cyan incoming handles / logo lettering is entirely outlined',fontsize=13,color=(.7,.8,.9))
    for i,c in enumerate(cs):
        col=i%9;row=i//9;x=48+col*233;y=106+row*285
        p.draw_rect(fitz.Rect(x,y,x+217,y+259),color=(.2,.35,.48),width=.5)
        bx,by,bw,bh=c['bbox'];scale=min(185/bw,170/bh)
        tf=lambda a,b:(x+108+(a-bx-bw/2)*scale,y+110+(b-by-bh/2)*scale)
        draw(p,c,ocgs[c['id']],True,tf,PALETTE[i%len(PALETTE)])
        for j,h in enumerate(c['handles']):
            a=fitz.Point(*tf(*h['anchor']));b=fitz.Point(*tf(*h['control']));color=rgb('#ff72d2' if j%2==0 else '#57e1ed')
            p.draw_line(a,b,color=color,width=.5,oc=ocgs[c['id']]);p.draw_circle(b,1.7,color=color,fill=color,oc=ocgs[c['id']])
        for a in c['anchors']:
            a,b=tf(*a);p.draw_rect(fitz.Rect(a-1.8,b-1.8,a+1.8,b+1.8),color=(1,1,1),fill=(.04,.12,.2),width=.6,oc=ocgs[c['id']])
        p.insert_text((x+9,y+221),c['id'],fontsize=10,color=(1,1,1))
        p.insert_text((x+9,y+241),f'{c["nodes"]} anchors / {c["cubic_segments"]} cubic segments',fontsize=10,color=(.7,.8,.9))
    doc.set_metadata({'title':'KESWA - layered vector masters and component blueprint','author':'','subject':'17 named PDF optional-content layers; all logo lettering is paths'})
    path=OUT/'KESWA_Vector_Layered.pdf';doc.save(path,garbage=4,deflate=True)
    for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(.65,.65)).save(ROOT/'verification'/f'pdf-page-{i+1}.png')
    doc.close()

def dxf(cs):
    doc=ezdxf.new('R2013');doc.units=0;msp=doc.modelspace()
    for c in cs:
        layer=c['id'].upper();doc.layers.new(layer,dxfattribs={'true_color':int(c['color_light'][1:],16)})
        p=start=None
        def v(a):return (a[0],H-a[1],0)
        for op,a in parse(c['d']):
            if op=='M':p=a;start=a
            elif op=='L':msp.add_line(v(p),v(a),dxfattribs={'layer':layer});p=a
            elif op=='C':
                s=msp.add_spline(degree=3,dxfattribs={'layer':layer});s.control_points=[v(p),v(a[:2]),v(a[2:4]),v(a[4:])];s.knots=[0,0,0,0,1,1,1,1];p=a[4:]
            else:
                if p!=start:msp.add_line(v(p),v(start),dxfattribs={'layer':layer})
                p=start
    doc.saveas(OUT/'KESWA_CAD_Ready.dxf')

def bundle():
    with zipfile.ZipFile(OUT/'KESWA_Vector_Asset_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            if f.is_file() and f.suffix.lower() in ['.ai','.svg','.eps','.dxf','.pdf','.png']:
                z.write(f,f.suffix[1:].upper()+'/'+f.name)
        for folder,fmt in [('individual_svgs','SVG'),('individual_pngs','PNG')]:
            for f in sorted((OUT/folder).glob('*')):z.write(f,fmt+'/'+folder+'/'+f.name)
        for name in ['components.json','README.txt','validation.json']:z.write(OUT/name,name)


def main():
    OUT.mkdir(exist_ok=True);(ROOT/'verification').mkdir(exist_ok=True)
    cs=[enrich(c) for c in build_components()];assert len(cs)==17
    data={'width':W,'height':H,'coordinate_system':'source-light.png pixels, y down','components':cs}
    (OUT/'components.json').write_text(json.dumps(data,indent=2))
    for dark in [False,True]:
        suffix='Dark' if dark else 'Light'
        (OUT/f'KESWA_Master_Layered_{suffix}.svg').write_text(svg(cs,dark))
        png(cs,OUT/f'KESWA_Transparent_{suffix}_3840px.png',dark=dark)
    for d in ['individual_svgs','individual_pngs']:(OUT/d).mkdir(exist_ok=True)
    for c in cs:
        x,y,w,h=c['bbox'];box=[x-8,y-8,w+16,h+16]
        (OUT/'individual_svgs'/f'{c["id"]}.svg').write_text(svg([c],box=box))
        for dark in [False,True]:png([c],OUT/'individual_pngs'/f'{c["id"]}_{"Dark" if dark else "Light"}.png',width=1024,dark=dark,box=box)
    (OUT/'KESWA_Vector_Master.eps').write_text(ps(cs))
    (OUT/'KESWA_Master_Layered.ai').write_text(ps(cs,True))
    pdf(cs);dxf(cs)
    readme='''KESWA ELECTRICAL / CUBIC BEZIER VECTOR LIBRARY
17 independent named components. All logo lettering is outlined; no font dependency.
Source coordinates: actual supplied light raster is 2172 x 724, not 1920 x 666.
Light #252A2D + #0043C2. Reversed #FFFFFF + #0052FF.
SVG: 17 named Inkscape layer groups; individual SVGs have padded artboards.
PDF: 3 pages, 17 named optional-content layers. Page 3 labels are annotation text.
DXF: R2013, 17 named component layers, exact LINE and degree-3 clamped SPLINE entities.
DXF units are source pixels / unitless. Set physical scale before manufacture.
EPS: Level 3 PostScript, named object comments and Illustrator layer records.
AI: legacy Illustrator PostScript interchange with named AI layer records. This is
NOT an Adobe-generated native CC PDF/private-data hybrid. Illustrator CC import,
layer retention and native resave must be checked in Adobe Illustrator, unavailable
in the build environment. The .ai is not a renamed PDF.
PNG: transparent raster companions; PNG cannot preserve editable vector layers.
Individual light and reversed PNGs are included for separate placement.
Source raster noise is intentionally not reproduced. See validation.json and
geometry-fit-report.json (when present) for measured error; exact subpixel fidelity
to every noisy source edge is not claimed.
Application boards are conceptual layouts, not manufactured product certification.
'''
    (OUT/'README.txt').write_text(readme)
    doc=fitz.open(OUT/'KESWA_Vector_Layered.pdf');cad=ezdxf.readfile(OUT/'KESWA_CAD_Ready.dxf');audit=cad.audit()
    import xml.etree.ElementTree as ET
    for f in (OUT/'individual_svgs').glob('*.svg'):ET.parse(f)
    for f in OUT.glob('*.svg'):ET.parse(f)
    validation={'component_count':len(cs),'anchors_total':sum(c['nodes'] for c in cs),'curved_glyphs':{c['id']:{'anchors':c['nodes'],'cubic_segments':c['cubic_segments']} for c in cs if c['cubic_segments']},'pdf_pages':len(doc),'pdf_named_layers':len(doc.get_ocgs()),'dxf_component_layers':[l.dxf.name for l in cad.layers if re.match(r'\d\d_',l.dxf.name)],'dxf_audit_errors':len(audit.errors),'dxf_splines':len(cad.modelspace().query('SPLINE')),'svg_xml_valid':True,'illustrator_cc_roundtrip':'NOT TESTED - Illustrator unavailable','ai_native_cc_hybrid':False,'png_preserves_layers':False,'logo_live_type':False}
    assert len(doc)==3 and len(doc.get_ocgs())==17 and not audit.errors
    for c in cs:
        assert c['nodes']<35
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2));bundle()
    with zipfile.ZipFile(OUT/'KESWA_Vector_Asset_Pack.zip') as z:assert z.testzip() is None;validation['zip_members']=len(z.namelist())
    print(json.dumps(validation,indent=2))
if __name__=='__main__':main()
