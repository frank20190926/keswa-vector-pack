"""KESWA reconstruction: explicit CAD topology and source-isocontour cubic fitting.
No fonts or polygonized curved glyphs. Coordinates are source-image pixels.
"""
from pathlib import Path
import json, re
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
import contourpy
ROOT=Path(__file__).resolve().parent
REF=ROOT/'geometry_reference_v1.json'
if not REF.exists(): REF.write_bytes((ROOT/'exports/components.json').read_bytes())
# Control points encode intended tangent directions; least-squares fits handle lengths.
CURVES={
3: 'M 954 179 L 1164.5 179 L 1177 212 C 1181 223 1181.5 234 1181.5 245.75 L 992 245.75 C 982 245.75 977.5 252 977.5 262.5 C 977.5 273 982 279 992 279 L 1123 279 C 1185 279 1218 308 1218 362.5 C 1218 418 1185 447.25 1123 447.25 L 881.25 447.25 L 881.25 380 L 1093 380 C 1103 380 1108.5 374 1108.5 363.5 C 1108.5 353 1103 346.75 1093 346.75 L 955 346.75 C 900 346.75 871 316 871 263 C 871 211 902 179 954 179 Z',
5: 'M 1635.25 445.75 L 1736.5 445.75 L 1856.5 264.75 L 1972.25 445.75 L 2077.75 445.75 L 1919.75 188.25 C 1916 182 1912 179 1903 179 L 1803.25 179 C 1799.5 181 1797 186 1793 192 Z',
10:'M 936.5 513.8 L 913.8 524 C 907 515.5 898 510.5 886 510.5 C 869 510.5 856 520.5 856 535 C 856 549.5 869 559.7 886 559.7 C 898 559.7 908 555 914 546.8 L 936.5 556.8 C 927 571.8 909 580.6 886 580.6 C 854 580.6 828 560.6 828 535 C 828 509.4 854 489 886 489 C 909 489 927 498 936.5 513.8 Z',
12:'M 1173.2 491.5 L 1233 491.5 C 1259 491.5 1271.8 502.5 1271.8 522 C 1271.8 535 1265 544 1250.8 550 L 1273.7 578.7 L 1242.5 578.7 L 1221.5 552.8 L 1199.7 552.8 L 1199.7 578.7 L 1173.2 578.7 Z M 1199.7 511.8 L 1233 511.8 C 1241 511.8 1245 515.5 1245 522 C 1245 529 1241 533 1233 533 L 1199.7 533 Z',
14:'M 1560.5 513.8 L 1537.8 524 C 1531 515.5 1522 510.5 1510 510.5 C 1493 510.5 1480 520.5 1480 535 C 1480 549.5 1493 559.7 1510 559.7 C 1522 559.7 1532 555 1538 546.8 L 1560.5 556.8 C 1551 571.8 1533 580.6 1510 580.6 C 1478 580.6 1452 560.6 1452 535 C 1452 509.4 1478 489 1510 489 C 1533 489 1551 498 1560.5 513.8 Z',
}
STRAIGHT={
8:'M 504.1 491.5 L 530.75 491.5 L 530.75 558.75 L 588.5 558.75 L 588.5 578.62 L 504.1 578.62 Z',
11:'M 1005.25 491.5 L 1098.5 491.5 L 1098.5 512 L 1064.62 512 L 1064.62 578.62 L 1038 578.62 L 1038 512 L 1005.25 512 Z',
13:'M 1351 491.5 L 1377.62 491.5 L 1377.62 578.62 L 1351 578.62 Z',
15:'M 1618 578.7 L 1666.5 491.5 L 1688.5 491.5 L 1735.75 578.7 L 1708.25 578.7 L 1700.5 563.75 L 1654.25 563.75 L 1646.5 578.7 Z M 1677.5 518.75 L 1663.75 545 L 1690 545 Z',
16:'M 1802 491.5 L 1829.75 491.5 L 1829.75 558.75 L 1888.5 558.75 L 1888.5 578.62 L 1802 578.62 Z',
}
def parse(d):
 toks=re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?',d); out=[];i=0
 while i<len(toks):
  op=toks[i];i+=1;n={'M':2,'L':2,'C':6,'Z':0}[op]
  out.append([op,np.array(list(map(float,toks[i:i+n]))).reshape(-1,2)]);i+=n
 return out

def bez(p,t):
 t=np.asarray(t)[:,None];u=1-t
 return u**3*p[0]+3*u*u*t*p[1]+3*u*t*t*p[2]+t**3*p[3]

def fit_cubic(points,p0,p3,guess,directions=None):
 v1,v2 = directions if directions is not None else (guess[0]-p0,guess[1]-p3)
 v1=v1.copy();v2=v2.copy()
 v1/=np.linalg.norm(v1);v2/=np.linalg.norm(v2)
 dif=np.linalg.norm(np.diff(points,axis=0),axis=1);t=np.r_[0,np.cumsum(dif)];t/=t[-1]
 for _ in range(10):
  u=1-t;b1=3*u*u*t;b2=3*u*t*t
  base=(u**3+b1)[:,None]*p0+(b2+t**3)[:,None]*p3
  A=np.stack([b1[:,None]*v1,b2[:,None]*v2],axis=-1).reshape(-1,2)
  lens=np.linalg.lstsq(A,(points-base).ravel(),rcond=None)[0]
  lens=np.maximum(lens,.1);p=np.array([p0,p0+lens[0]*v1,p3+lens[1]*v2,p3])
  q=bez(p,t);d=3*((1-t)**2)[:,None]*(p[1]-p[0])+6*((1-t)*t)[:,None]*(p[2]-p[1])+3*(t*t)[:,None]*(p[3]-p[2])
  dd=6*(1-t)[:,None]*(p[2]-2*p[1]+p[0])+6*t[:,None]*(p[3]-2*p[2]+p[1])
  den=np.sum(d*d+(q-points)*dd,axis=1);t=np.clip(t-np.sum((q-points)*d,axis=1)/np.maximum(den,1e-6),0,1)
 return p[1:3]

def contours_for(c,img):
 x,y,w,h=c['bbox'];x=max(0,int(x)-8);y=max(0,int(y)-8)
 rgb=img[y:int(y+h+16),x:int(x+w+16)]
 fg=np.array([37,42,45]) if c['color_light']=='#252A2D' else np.array([0,67,194])
 v=255-fg;alpha=np.sum((255-rgb)*v,axis=-1)/np.sum(v*v)
 alpha=gaussian_filter(alpha,.55)
 lines=contourpy.contour_generator(z=alpha).lines(.5)
 return [l+np.array([x+.5,y+.5]) for l in lines if len(l)>20]

def refine(c,d,img):
 ops=parse(d); lines=contours_for(c,img);groups=[];cur=[]
 for op,pts in ops:
  if op=='M' and cur:groups.append(cur);cur=[]
  cur.append([op,pts])
 if cur:groups.append(cur)
 out=[]
 for group in groups:
  targets=np.array([pts[-1] for op,pts in group if op!='Z'])
  line=min(lines,key=lambda a:np.mean(cKDTree(a).query(targets)[0]))
  # Set traversal direction from second target relative to first along contour.
  idx=cKDTree(line).query(targets)[1];n=len(line)-1
  forward=(idx[1]-idx[0])%n;backward=(idx[0]-idx[1])%n
  if forward>backward:line=line[::-1];idx=cKDTree(line).query(targets)[1]
  # Keep intended extrema exactly horizontal/vertical; isocontour interpolation is subpixel.
  anchors=line[idx].copy()
  def arc_between(a,b):
   return line[a:b+1] if b>=a else np.vstack([line[a:-1],line[:b+1]])
  straight={}; nonz=[(op,pts) for op,pts in group if op!='Z']
  for k,(op,pts) in enumerate(nonz):
   # Last -> first closes by a straight segment unless the final C already closed it.
   if op!='L' and not (k==0 and np.linalg.norm(targets[-1]-targets[0])>.01):continue
   arc=arc_between(idx[k-1],idx[k]); dist=np.linalg.norm(np.diff(arc,axis=0),axis=1); along=np.r_[0,np.cumsum(dist)]
   trim=min(5.,along[-1]*.15);core=arc[(along>trim)&(along<along[-1]-trim)]
   if len(core)<3:continue
   origin=core.mean(0);_,_,vh=np.linalg.svd(core-origin,full_matrices=False);normal=vh[1]
   straight[k]=(normal,float(normal@origin))
  for k in range(len(anchors)):
   before=straight.get(k);after=straight.get((k+1)%len(anchors))
   if before is not None and after is not None:
    A=np.array([before[0],after[0]])
    if abs(np.linalg.det(A))>.05:
     cross=np.linalg.solve(A,np.array([before[1],after[1]]))
     if np.linalg.norm(cross-anchors[k])<5:
      # Blur at an acute raster corner recedes from the ideal intersection.
      # Bound the extrapolation to 0.85 source pixels without adding a roundover
      # or any extra node; both neighbouring edges remain exact CAD lines.
      distance,nearest=cKDTree(line).query(cross)
      if distance>.85:cross+=(line[nearest]-cross)*(1-.85/distance)
      anchors[k]=cross
   elif before is not None or after is not None:
    normal,offset=before if before is not None else after
    anchors[k]-=normal*(normal@anchors[k]-offset)
  # Duplicate endpoint of a closed cubic shares the initial anchor.
  if np.linalg.norm(targets[-1]-targets[0])<.01:anchors[-1]=anchors[0]
  j=0;prev=None
  for op,pts in group:
   if op=='Z':out.append([op,pts]);continue
   end=anchors[j]
   if op=='C':
    a=idx[j-1];b=idx[j];arc=line[a:b+1] if b>=a else np.vstack([line[a:-1],line[:b+1]])
    controls=fit_cubic(arc,prev,end,pts[:2],(pts[0]-targets[j-1],pts[1]-targets[j]))
    out.append([op,np.vstack([controls,end])])
   else:out.append([op,np.array([end])])
   prev=end;j+=1
 return out

def serialize(ops):
 return ' '.join(op+(' '+' '.join(f'{v:.3f}'.rstrip('0').rstrip('.') for v in pts.ravel()) if len(pts) else '') for op,pts in ops)

def sample(ops):
 out=[];p=None;start=None
 for op,a in ops:
  if op=='M':p=a[0];start=p;out.append(p[None,:])
  elif op=='L':out.append(np.linspace(p,a[0],max(3,int(np.linalg.norm(a[0]-p)*3))));p=a[0]
  elif op=='C':out.append(bez(np.vstack([p,a]),np.linspace(0,1,240)));p=a[-1]
  else:out.append(np.linspace(p,start,max(3,int(np.linalg.norm(p-start)*3))));p=start
 return np.vstack(out)

def build_components():
 img=np.asarray(Image.open(ROOT/'assets/source-light.png').convert('RGB'),float)
 comps=json.loads(REF.read_text())['components'];report={}
 for i,c in enumerate(comps):
  ops=refine(c,CURVES[i],img) if i in CURVES else parse(STRAIGHT.get(i,c['d']))
  c['d']=serialize(ops);c.pop('polys',None)
  pts=sample(ops);lo=pts.min(0);hi=pts.max(0)
  c['bbox']=[round(float(v),3) for v in [*lo,*(hi-lo)]]
  anchors=[];handles=[];prev=None;start=None
  for op,a in ops:
   if op=='Z':prev=start;continue
   if op=='M':start=a[-1]
   if op=='C':handles.extend([{'anchor':prev.tolist(),'control':a[0].tolist()},{'anchor':a[-1].tolist(),'control':a[1].tolist()}])
   # Closed cubic ending at the first anchor is not a new node.
   if not (op=='C' and np.linalg.norm(a[-1]-start)<.001):anchors.append(a[-1].tolist())
   prev=a[-1]
  c['nodes']=len(anchors);c['anchor_count']=len(anchors);c['anchors']=anchors;c['handles']=handles
  c['cubic_segments']=sum(op=='C' for op,a in ops)
  if i in CURVES:
   edge=np.vstack(contours_for(c,img));err=cKDTree(edge).query(pts)[0]
   c['source_edge_error_px']={'mean':round(float(err.mean()),3),'p95':round(float(np.quantile(err,.95)),3),'max':round(float(err.max()),3),'method':'curve samples to Gaussian-0.55px alpha-0.5 source isocontour; not whole-image pixel equality'}
 return comps
if __name__=='__main__':
 c=build_components()
 for g in c:print(g['id'],g['nodes'],g['cubic_segments'],g.get('source_edge_error_px',''))
 Path('/tmp/keswa-geometry-preview.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2172 724">'+''.join(f'<path d="{g["d"]}" fill="{g["color_light"]}" fill-rule="evenodd"/>' for g in c)+'</svg>')
