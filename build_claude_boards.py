#!/usr/bin/env python3
"""Generate board1-claude.html, board2-claude.html, index.html from exports/components.json.
Read-only on exports/. Re-run after the vector data changes (handles/anchors are data-driven)."""
import json, re, colorsys, math, os, html
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'exports/components.json')))
W, H = D['width'], D['height']
C = D['components']
for c in C:
    c['n'] = c['id'][:2]

# ---------- path parsing (M/L/C/Z) ----------
def parse(d):
    toks = re.findall(r'[MLCZ]|-?\d+\.?\d*', d)
    anchors, handles, ncubic = [], [], 0
    i, cmd, prev = 0, None, None
    while i < len(toks):
        t = toks[i]
        if t in 'MLCZ':
            cmd = t; i += 1
            if t == 'Z': continue
            continue
        if cmd in 'ML':
            p = (float(toks[i]), float(toks[i+1])); i += 2
            anchors.append(p); prev = p
        elif cmd == 'C':
            v = [float(x) for x in toks[i:i+6]]; i += 6
            c1, c2, p = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            handles.append((prev, c1)); handles.append((p, c2))
            anchors.append(p); prev = p; ncubic += 1
        else:
            i += 1
    return anchors, handles, ncubic

for c in C:
    a, h, nc = parse(c['d'])
    c['anchors'], c['handles'], c['ncubic'] = a, h, nc
    c['nanch'] = len(a)
    xs = [p[0] for p in a]; ys = [p[1] for p in a]
    c['bb'] = (min(xs), min(ys), max(xs), max(ys))
    c['holes'] = max(0, c['d'].count('M') - 1)
    c['hue'] = None
for k, c in enumerate(C):
    r, g, b = colorsys.hls_to_rgb((k * 0.0588 + 0.02) % 1, 0.58, 0.85)
    c['col'] = '#%02X%02X%02X' % (int(r*255), int(g*255), int(b*255))
TOTAL_CUBIC = sum(c['ncubic'] for c in C)
CURVE_WORD = 'cubic Bézier' if TOTAL_CUBIC else 'outlined polygon'

MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
SANS = "-apple-system,'Helvetica Neue',Helvetica,Arial,sans-serif"
LIGHT, LBLUE, DARKC, DBLUE = '#252A2D', '#0043C2', '#FFFFFF', '#0052FF'

def f(x): return ('%.2f' % x).rstrip('0').rstrip('.')

def nodes_svg(c, s, col=None, fill='#0B1220', maxn=None):
    """anchor squares (+cubic handles) in glyph units; s = unit size of a square."""
    col = col or c['col']
    out = []
    for a, hnd in c['handles']:
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (f(a[0]), f(a[1]), f(hnd[0]), f(hnd[1]), col, f(s*0.2)))
        out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (f(hnd[0]), f(hnd[1]), f(s*0.5), col, col, f(s*0.15)))
    pts = c['anchors']
    for x, y in pts:
        out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (f(x-s/2), f(y-s/2), f(s), f(s), fill, col, f(s*0.28)))
    return ''.join(out)

def path(c, fill, extra=''):
    return '<path d="%s" fill="%s" fill-rule="evenodd" %s/>' % (c['d'], fill, extra)

def fills(mode):
    return (lambda c: c['color_light']) if mode == 'light' else (lambda c: c['color_dark'])

def master(mode, ids=None):
    fl = fills(mode)
    return ''.join(path(c, fl(c)) for c in C if ids is None or c['n'] in ids)

def tag(x, y, text, col, fs=20, w=56, h=28):
    return ('<g transform="translate(%s,%s)"><rect x="%s" y="0" width="%s" height="%s" rx="4" fill="#0B1528" stroke="%s" stroke-width="2"/>'
            '<text x="0" y="%s" text-anchor="middle" fill="#F8FAFC" font-family="%s" font-size="%s" font-weight="800">%s</text></g>'
            % (f(x), f(y), f(-w/2), w, h, col, f(h*0.7), MONO, fs, text))

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(w)spx;height:%(h)spx;overflow:hidden;background:#070D19;color:#E6EDF7;font-family:%(sans)s}
.sheet{position:relative;width:%(w)spx;height:%(h)spx;overflow:hidden;
 background:linear-gradient(#0B1626,#070D19);}
.sheet:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(56,110,220,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(56,110,220,.07) 1px,transparent 1px);background-size:32px 32px;pointer-events:none}
.hdr{position:absolute;left:24px;top:14px;right:24px;height:48px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1E3A6E}
.hdr .eb{font:700 10.5px %(mono)s;letter-spacing:.16em;text-transform:uppercase;color:#5B9BFF}
.hdr .tt{font:800 20px %(sans)s;letter-spacing:-.01em;color:#fff;margin-top:3px}
.hdr .tt b{color:#5B9BFF}
.hdr .rt{font:600 10.5px %(mono)s;color:#8FA3C4;text-align:right;line-height:1.5}
.panel{position:absolute;background:rgba(13,24,44,.92);border:1px solid #1E3A6E;border-radius:6px;overflow:hidden}
.ph{height:30px;display:flex;align-items:center;justify-content:space-between;padding:0 12px;border-bottom:1px solid #1E3A6E;font:800 10.5px %(mono)s;letter-spacing:.08em;text-transform:uppercase;color:#CFE0FF}
.ph i{font-style:normal;color:#5B9BFF;font-weight:700}
svg{display:block}
""" % dict(w=1600, h=1200, sans=SANS, mono=MONO)

def page(title, css, body):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>%s</title>'
            '<meta name="viewport" content="width=1600"><style>%s</style></head><body>%s</body></html>' % (title, BASE_CSS + css, body))

# =====================================================================
# BOARD 1
# =====================================================================
def board1():
    # ---- left panel: outline blueprint ----
    VX, VY, VW, VH = 130, 110, 1990, 520
    sc = 968 / VW
    s_main = 5 / sc
    main = ['<svg x="16" y="44" width="968" height="%s" viewBox="%d %d %d %d">' % (f(VH*sc), VX, VY, VW, VH),
            '<rect x="%d" y="%d" width="%d" height="%d" fill="#08111F"/>' % (VX, VY, VW, VH)]
    # ruler baseline guides
    for gy, lab in ((179, 'CAP'), (447, 'BASE'), (491, 'SUB-CAP'), (579, 'SUB-BASE')):
        main.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#1E3A6E" stroke-width="1.5" stroke-dasharray="10 8"/><text x="%d" y="%d" fill="#4B6AA0" font-size="17" font-family="%s">%s</text>' % (VX, gy, VX+VW, gy, VX+6, gy-5, MONO, lab))
    for c in C:
        x0, y0, x1, y1 = c['bb']
        main.append('<g>')
        main.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="7 5" opacity=".75"/>' % (f(x0-5), f(y0-5), f(x1-x0+10), f(y1-y0+10), c['col']))
        main.append(path(c, c['col'], 'fill-opacity=".14" stroke="%s" stroke-width="%s"' % (c['col'], f(1.3/sc))))
        ss = s_main if c['nanch'] <= 40 else s_main * 0.55
        main.append(nodes_svg(c, ss))
        cx = (x0 + x1) / 2
        if c['n'] == '07':
            main.append(tag(cx, y1 + 10, c['n'], c['col']))
        elif int(c['n']) <= 6:
            main.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2"/>' % (f(cx), f(y0-5), f(cx), f(y0-24), c['col']))
            main.append(tag(cx, y0 - 52, c['n'], c['col']))
        else:
            main.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2"/>' % (f(cx), f(y1+5), f(cx), f(y1+22), c['col']))
            main.append(tag(cx, y1 + 22, c['n'], c['col'], fs=18, w=48, h=26))
        main.append('</g>')
    main.append('</svg>')
    main_h = VH * sc
    # ---- inset zoom row ----
    insets = [('04', ['04'], 'S · Curved Glyph'), ('06', ['06', '07'], 'A · Arch + Delta'), ('11', ['11'], 'C · Sub-glyph'), ('13', ['13'], 'R · Sub-glyph')]
    iy = 44 + main_h + 12
    ih = 570 - iy - 14
    iw = (968 - 30) / 4
    ins = []
    for k, (lead, ids, cap) in enumerate(insets):
        cs = [c for c in C if c['n'] in ids]
        x0 = min(c['bb'][0] for c in cs); y0 = min(c['bb'][1] for c in cs)
        x1 = max(c['bb'][2] for c in cs); y1 = max(c['bb'][3] for c in cs)
        pad = 8
        bw, bh = iw - 16, ih - 30
        s = min(bw / (x1 - x0 + 2*pad), bh / (y1 - y0 + 2*pad))
        vw, vh = bw / s, bh / s
        vx = (x0 + x1) / 2 - vw / 2; vy = (y0 + y1) / 2 - vh / 2
        ins.append('<g transform="translate(%s,%s)"><rect width="%s" height="%s" fill="#08111F" stroke="#1E3A6E"/>' % (f(16 + k*(iw+10)), f(iy), f(iw), f(ih)))
        ins.append('<svg x="8" y="8" width="%s" height="%s" viewBox="%s %s %s %s">' % (f(bw), f(bh), f(vx), f(vy), f(vw), f(vh)))
        for c in cs:
            ins.append(path(c, c['col'], 'fill-opacity=".14" stroke="%s" stroke-width="%s"' % (c['col'], f(1.2/s))))
            ins.append(nodes_svg(c, 4.5 / s * (1 if c['nanch'] <= 40 else .6)))
        ins.append('</svg>')
        label = ' + '.join('%s' % c['id'] for c in cs)
        info = '/'.join(str(c['nanch']) for c in cs) + ' anchors' + (' · %d cubic seg.' % sum(c['ncubic'] for c in cs) if TOTAL_CUBIC else ' · no handles')
        ins.append('<text x="8" y="%s" fill="#CFE0FF" font-size="10" font-family="%s" font-weight="800">%s</text>' % (f(ih-17), MONO, html.escape(label)))
        ins.append('<text x="8" y="%s" fill="#6F86AE" font-size="9" font-family="%s">%s</text></g>' % (f(ih-5), MONO, html.escape(info)))
    left = ('<div class="panel" style="left:24px;top:72px;width:1000px;height:600px"><div class="ph"><span>A · Ctrl+Y Outline View — Anchor Nodes ■ %s</span><i>17 colour-coded groups · 0 live type</i></div>'
            '<svg width="1000" height="570">%s%s</svg></div>') % ('&amp; Bézier Handles ●—●' if TOTAL_CUBIC else '(per-path anchors)', ''.join(main), ''.join(ins))
    # ---- right panel: layer stack + master previews ----
    rows = []
    for k, c in enumerate(C):
        y = 40 + k * 21
        rows.append('<g transform="translate(12,%d)"><rect width="516" height="19" rx="3" fill="%s"/>' % (y, '#10213D' if k % 2 == 0 else '#0D1A31'))
        rows.append('<rect x="6" y="5" width="9" height="9" fill="%s"/>' % c['col'])
        rows.append('<text x="24" y="13.5" fill="#8FA3C4" font-size="10" font-family="%s">%s</text>' % (MONO, c['n']))
        rows.append('<text x="46" y="13.5" fill="#F1F6FF" font-size="11" font-weight="800" font-family="%s">%s</text>' % (MONO, c['id']))
        grp = {'KESWA_Primary_Wordmark': 'WORDMARK', 'KESWA_Accent_Mark': 'ACCENT', 'ELECTRICAL_Submark': 'SUBMARK'}[c['group']]
        rows.append('<text x="330" y="13.5" fill="#5B9BFF" font-size="9" font-family="%s">%s</text>' % (MONO, grp))
        rows.append('<text x="508" y="13.5" text-anchor="end" fill="#8FA3C4" font-size="9.5" font-family="%s">%d pts%s</text>' % (MONO, c['nanch'], ' +hole' if c['holes'] else ''))
        rows.append('<text x="440" y="13.5" fill="#6F86AE" font-size="9" font-family="%s">closed</text></g>' % MONO if False else '</g>')
    py = 40 + 17 * 21 + 14
    prev = ('<g transform="translate(12,%d)">' % py +
            '<rect width="252" height="%d" fill="#FFFFFF" rx="4"/><svg x="10" y="12" width="232" height="%d" viewBox="150 160 1950 440">%s</svg>' % (570-py-22, 77, master('light')) +
            '<text x="8" y="%d" fill="#252A2D" font-size="9.5" font-weight="800" font-family="%s">LIGHT MASTER  #252A2D + #0043C2</text>' % (570-py-34, MONO) +
            '<g transform="translate(264,0)"><rect width="252" height="%d" fill="#04070D" rx="4" stroke="#1E3A6E"/><svg x="10" y="12" width="232" height="77" viewBox="150 160 1950 440">%s</svg>' % (570-py-22, master('dark')) +
            '<text x="8" y="%d" fill="#FFFFFF" font-size="9.5" font-weight="800" font-family="%s">DARK REVERSED  #FFFFFF + #0052FF</text></g></g>' % (570-py-34, MONO))
    right = ('<div class="panel" style="left:1036px;top:72px;width:540px;height:600px"><div class="ph"><span>B · Illustrator CC Layer Stack</span><i>17 / 17 named</i></div>'
             '<svg width="540" height="570"><text x="12" y="34" fill="#4B6AA0" font-size="9" font-family="%s">IDX  LAYER NAME · GROUP · TYPE · ANCHORS</text>%s%s</svg></div>') % (MONO, ''.join(rows), prev)
    # ---- cards ----
    cards = []
    cw = (1552 - 64) / 9
    chh = (492 - 8) / 2
    for k, c in enumerate(C):
        col, row = k % 9, k // 9
        x0, y0, x1, y1 = c['bb']
        bw, bh = x1 - x0, y1 - y0
        aw, ah = cw - 16, 112
        s = min((aw - 24) / bw, (ah - 24) / bh)
        vw, vh = aw / s, ah / s
        vx, vy = (x0 + x1)/2 - vw/2, (y0 + y1)/2 - vh/2
        ptype = 'Compound Path · %d hole%s' % (c['holes'], 's' if c['holes'] > 1 else '') if c['holes'] else 'Closed Path · Outlined'
        cards.append(
            '<div class="card" style="left:%spx;top:%spx;width:%spx;height:%spx">'
            '<div class="ch"><b style="background:%s"></b><span>#%s</span><em>%s</em></div>'
            '<svg width="%s" height="%d" viewBox="%s %s %s %s" style="margin:0 8px;background:#EEF2F6;border:1px solid #C9D4E4">'
            '<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s" stroke-dasharray="%s"/>%s</svg>'
            '<div class="cn">%s</div><div class="cl">%s</div><div class="cl">%d anchor nodes</div><div class="cl dim">%d × %d u · %s</div></div>'
            % (f(24 + col*(cw+8)), f(684 + row*(chh+8)), f(cw), f(chh), c['col'], c['n'], c['group'].replace('KESWA_', '').replace('_', ' '),
               f(aw), ah, f(vx), f(vy), f(vw), f(vh), f(x0-3/s), f(y0-3/s), f(bw+6/s), f(bh+6/s), c['col'], f(1/s), f(4/s) + ' ' + f(3/s),
               path(c, c['color_light']), c['id'], ptype, c['nanch'], bw, bh, c['color_light']))
    cards.append('<div class="card info" style="left:%spx;top:%spx;width:%spx;height:%spx"><div class="ih">LIBRARY</div><div class="iv">17</div><div class="cl">individually selectable closed vector pieces</div><div class="cl">3 groups: wordmark · accent · submark</div><div class="cl">0 live type · 0 raster</div><div class="cl">Drop-in: copy any piece into any layout</div></div>'
                 % (f(24 + 8*(cw+8)), f(684 + (chh+8)), f(cw), f(chh)))
    css = """
.card{position:absolute;background:rgba(13,24,44,.95);border:1px solid #1E3A6E;border-radius:5px;overflow:hidden;padding-bottom:6px}
.ch{display:flex;align-items:center;gap:6px;height:28px;padding:0 8px;font:800 10px %(mono)s;color:#CFE0FF}
.ch b{width:9px;height:9px;display:block}.ch span{color:#fff}.ch em{font-style:normal;color:#5B9BFF;margin-left:auto;font-size:8.5px;letter-spacing:.05em;text-transform:uppercase}
.cn{font:800 9.6px %(mono)s;color:#F1F6FF;padding:7px 8px 2px}.cl{font:600 9.2px %(mono)s;color:#9DB3D6;padding:1.5px 8px}.cl.dim{color:#5E759E}
.info{display:flex;flex-direction:column;justify-content:center;border-color:#2F6BFF;background:linear-gradient(160deg,#0F2347,#0B1628)}
.ih{font:800 10px %(mono)s;letter-spacing:.16em;color:#5B9BFF;padding:0 8px}.iv{font:800 58px %(sans)s;color:#fff;padding:2px 8px 6px;line-height:1}
""" % dict(mono=MONO, sans=SANS)
    hdr = ('<div class="hdr"><div><div class="eb">Contest #2800912 · AI Image to Vector Pack · KESWA ELECTRICAL</div>'
           '<div class="tt">Sheet 01 · <b>17-Layer Vector Decomposition</b>, Ctrl+Y Node Blueprint &amp; Asset Library</div></div>'
           '<div class="rt">.AI (CC) · .SVG · .EPS · .PNG · .DXF · .PDF<br>100%% outlined · zero live type · %s paths</div></div>' % CURVE_WORD)
    return page('Sheet 01 · KESWA ELECTRICAL Vector Decomposition', css, '<div class="sheet">' + hdr + left + right + ''.join(cards) + '</div>')

# =====================================================================
# BOARD 2
# =====================================================================
def explode_offsets():
    off = {}
    sub = 0
    for c in C:
        i = int(c['n'])
        cx = (c['bb'][0] + c['bb'][2]) / 2
        dx = (cx - 1086) * 0.28
        if i <= 6: dy = -400 + (i % 2) * 170
        elif i == 7: dy = -60
        else:
            dy = 120 + (sub % 2) * 170; sub += 1
        off[c['n']] = (dx, dy)
    return off

def board2():
    off = explode_offsets()
    # --- exploded view ---
    allb = []
    for c in C:
        dx, dy = off[c['n']]
        allb.append((c['bb'][0]+dx, c['bb'][1]+dy, c['bb'][2]+dx, c['bb'][3]+dy))
    ux0 = min(b[0] for b in allb) - 110; ux1 = max(b[2] for b in allb) + 110
    uy0 = min(b[1] for b in allb) - 70; uy1 = max(b[3] for b in allb) + 70
    PW, PH = 800, 560
    s = min(PW / (ux1 - ux0), PH / (uy1 - uy0))
    vw, vh = PW / s, PH / s
    vx, vy = (ux0 + ux1)/2 - vw/2, (uy0 + uy1)/2 - vh/2
    hs = 6 / s
    ex = ['<svg x="4" y="34" width="%d" height="%d" viewBox="%s %s %s %s">' % (PW, PH, f(vx), f(vy), f(vw), f(vh))]
    for c in C:  # ghosts + leaders first
        dx, dy = off[c['n']]
        ex.append(path(c, 'none', 'stroke="#2A4577" stroke-width="%s" stroke-dasharray="%s"' % (f(1/s), f(4/s)+' '+f(3/s))))
    for c in C:
        dx, dy = off[c['n']]
        x0, y0, x1, y1 = c['bb']
        ex.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-dasharray="%s" opacity=".55"/>' % (f((x0+x1)/2), f((y0+y1)/2), f((x0+x1)/2+dx), f((y0+y1)/2+dy), c['col'], f(1/s), f(5/s)+' '+f(3/s)))
    for c in C:
        dx, dy = off[c['n']]
        x0, y0, x1, y1 = c['bb']
        ex.append('<g transform="translate(%s,%s)">' % (f(dx), f(dy)))
        # plane shadow
        ex.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" opacity=".08"/>' % (f(x0-14), f(y0-14), f(x1-x0+28), f(y1-y0+28), c['col']))
        ex.append(path(c, c['col']))
        bx0, by0, bx1, by1 = x0-8, y0-8, x1+8, y1+8
        ex.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#5B9BFF" stroke-width="%s"/>' % (f(bx0), f(by0), f(bx1-bx0), f(by1-by0), f(1.2/s)))
        for hx in (bx0, (bx0+bx1)/2, bx1):
            for hy in (by0, (by0+by1)/2, by1):
                if hx == (bx0+bx1)/2 and hy == (by0+by1)/2: continue
                ex.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#fff" stroke="#5B9BFF" stroke-width="%s"/>' % (f(hx-hs/2), f(hy-hs/2), f(hs), f(hs), f(1/s)))
        ex.append('<text x="%s" y="%s" text-anchor="middle" fill="#CFE0FF" font-size="%s" font-family="%s" font-weight="700">%s</text>' % (f((x0+x1)/2), f(by1 + 24/s), f(9/s), MONO, c['id']))
        ex.append('</g>')
    ex.append('</svg>')
    left = ('<div class="panel" style="left:24px;top:72px;width:808px;height:600px"><div class="ph"><span>A · Exploded Multi-Plane Layer Separation</span><i>17 objects · 0 merged · independent bounds</i></div><svg width="808" height="570" style="background:#08111F">%s</svg></div>' % ''.join(ex))
    # --- loupes ---
    # crop (cx, cy), title, caption
    ch = [a for a in C if a['n'] == '02'][0]
    ang = math.degrees(math.atan2(446.62 - 318.75, 435.25 - 278.62))
    gap = 278.62 - 275.62
    crops = [
        ((1200, 331), '04_S_Curved_Glyph', 'Fuzzy AI pixel staircase  →  %s edge' % CURVE_WORD),
        ((277, 312), '01_K_Vertical_Stem + 02_K_Diagonal_Chevron', 'Blurred AI seam  →  crisp %.1f u gap · %.1f° chevron edge' % (gap, ang)),
        ((1855, 326), '06_A_Rounded_Arch + 07_A_Delta_Triangle', 'Halation noise  →  exact #0043C2 delta (3 anchors)'),
    ]
    LW, LH = 340, 138
    zoom = 8
    vwu, vhu = LW / zoom, LH / zoom
    lo = []
    for k, ((cx, cy), ttl, cap) in enumerate(crops):
        y = 40 + k * 176
        vbx, vby = cx - vwu/2, cy - vhu/2
        vb = '%s %s %s %s' % (f(vbx), f(vby), f(vwu), f(vhu))
        lo.append('<text x="12" y="%d" fill="#F1F6FF" font-size="11" font-weight="800" font-family="%s">LOUPE %d · %s</text>' % (y - 6, MONO, k+1, ttl))
        lo.append('<text x="720" y="%d" text-anchor="end" fill="#5B9BFF" font-size="10" font-family="%s">800%%</text>' % (y - 6, MONO))
        # raster
        lo.append('<svg x="12" y="%d" width="%d" height="%d" viewBox="%s"><image href="assets/source-light.png" x="0" y="0" width="%d" height="%d" preserveAspectRatio="none"/></svg>' % (y, LW, LH, vb, W, H))
        lo.append('<rect x="12" y="%d" width="%d" height="%d" fill="none" stroke="#B45309" stroke-width="1.5"/>' % (y, LW, LH))
        lo.append('<rect x="12" y="%d" width="118" height="16" fill="#B45309"/><text x="18" y="%d" fill="#fff" font-size="9.5" font-weight="800" font-family="%s">ORIGINAL AI RASTER</text>' % (y, y + 11.5, MONO))
        # vector
        lo.append('<svg x="%d" y="%d" width="%d" height="%d" viewBox="%s"><rect x="%s" y="%s" width="%s" height="%s" fill="#FFFFFF"/>' % (12 + LW + 8, y, LW, LH, vb, f(vbx), f(vby), f(vwu), f(vhu)))
        near = [c for c in C if c['bb'][0] - 30 < cx + vwu/2 and c['bb'][2] + 30 > cx - vwu/2 and c['bb'][1] - 30 < cy + vhu/2 and c['bb'][3] + 30 > cy - vhu/2]
        for c in near:
            lo.append(path(c, c['color_light']))
        for c in near:
            lo.append(nodes_svg(c, 4.5 / zoom, col='#E11D48', fill='#fff'))
        if k == 1:
            lo.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#E11D48" stroke-width="%s"/>' % (f(275.62), f(cy-4), f(278.62), f(cy-4), f(1.2/zoom)))
        lo.append('</svg>')
        lo.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#2F6BFF" stroke-width="1.5"/>' % (12 + LW + 8, y, LW, LH))
        lo.append('<rect x="%d" y="%d" width="130" height="16" fill="#2F6BFF"/><text x="%d" y="%d" fill="#fff" font-size="9.5" font-weight="800" font-family="%s">CLEAN VECTOR PATH</text>' % (12 + LW + 8, y, 12 + LW + 14, y + 11.5, MONO))
        lo.append('<text x="12" y="%d" fill="#9DB3D6" font-size="10" font-family="%s">%s</text>' % (y + LH + 13, MONO, html.escape(cap)))
    right = ('<div class="panel" style="left:844px;top:72px;width:732px;height:600px"><div class="ph"><span>B · 800%% Macro Edge Audit — Raster vs Vector</span><i>red ■ = anchor nodes</i></div><svg width="732" height="570">%s</svg></div>' % ''.join(lo))

    # --- bottom cards ---
    CW = (1552 - 36) / 4
    def card(i, title, sub, inner, cap):
        return ('<div class="bc" style="left:%spx;top:684px;width:%spx;height:492px"><div class="bh"><b>%s</b><span>%s</span></div>%s<div class="bcap">%s</div></div>'
                % (f(24 + i*(CW+12)), f(CW), title, sub, inner, cap))
    def place(ids, tx, ty, scale, x0, y0, fill):
        return '<g transform="translate(%s,%s) scale(%s) translate(%s,%s)">%s</g>' % (f(tx), f(ty), f(scale), f(-x0), f(-y0), ''.join(path(c, fill if isinstance(fill, str) else fill(c)) for c in C if c['n'] in ids))
    kids = ['01', '02']
    # emblem
    def emblem(x, y, size, bg, kf, df, shape='rect'):
        s = 0.172
        inner = ('<g transform="translate(%s,%s) scale(%s)">' % (f(x), f(y), f(size/100)) +
                 ('<rect width="100" height="100" rx="22" fill="%s"/>' % bg if shape == 'rect' else '<circle cx="50" cy="50" r="50" fill="%s"/>' % bg) +
                 place(kids, 15, 22, s, 171, 179, kf) + place(['07'], 58, 71, s, 1775, 324, df) + '</g>')
        return inner
    em = ('<svg width="%s" height="300" viewBox="0 0 355 300" style="margin:0 12px;background:#0B1628;border:1px solid #1E3A6E">' % f(CW-24) +
          emblem(18, 24, 170, '#0A1426', DARKC, DBLUE) + emblem(205, 24, 120, '#FFFFFF', LIGHT, LBLUE, 'circ') +
          emblem(205, 160, 58, '#0043C2', DARKC, DARKC) + emblem(275, 160, 40, '#FFFFFF', LIGHT, LBLUE) + emblem(205, 232, 28, '#0A1426', DARKC, DBLUE) +
          '<text x="18" y="214" fill="#9DB3D6" font-size="9" font-family="%s">APP / HELMET BADGE · 01 + 02 + 07</text>' % MONO +
          '<text x="18" y="232" fill="#5E759E" font-size="8.5" font-family="%s">3 library pieces · 14 anchors total</text>' % MONO +
          '<text x="18" y="276" fill="#5E759E" font-size="8.5" font-family="%s">sizes 170 / 120 / 58 / 40 / 28 px</text></svg>' % MONO)
    c1 = card(0, '1 · Standalone Icon Emblem', 'pieces 01 + 02 + 07', em, 'Three drop-in pieces (K stem, K chevron, cobalt delta) re-composed into a compact badge. No redraw — the same closed paths, only transform + fill changed.')
    # van
    wm = ['01', '02', '03', '04', '05', '06']
    van = ('<svg width="%s" height="300" viewBox="0 0 355 300" style="margin:0 12px;background:#0B1628;border:1px solid #1E3A6E">' % f(CW-24) +
           '<rect x="0" y="236" width="355" height="64" fill="#0E1B31"/><ellipse cx="170" cy="236" rx="150" ry="5" fill="#000" opacity=".4"/>'
           '<path d="M18 222 V92 Q18 84 26 84 H228 V222 Z" fill="#F3F6FA"/>'
           '<path d="M228 100 H272 Q284 100 292 114 L318 150 Q324 158 324 168 V222 H228 Z" fill="#E4EAF2"/>'
           '<path d="M240 108 H268 Q276 108 282 118 L300 146 H240 Z" fill="#2B3A55"/>'
           '<line x1="228" y1="100" x2="228" y2="222" stroke="#B5C2D6" stroke-width="1"/><rect x="18" y="206" width="306" height="16" fill="#CDD7E5"/>'
           + place(wm, 34, 106, 0.0968, 171, 179, LIGHT) + place([c['n'] for c in C if int(c['n']) >= 8], 34, 140, 0.0968, 338, 491, LBLUE)
           + place(['07'], 150, 150, 0.46, 1775, 324, LBLUE) +
           '<circle cx="75" cy="224" r="19" fill="#141B28"/><circle cx="75" cy="224" r="9" fill="#8FA3C4"/><circle cx="270" cy="224" r="19" fill="#141B28"/><circle cx="270" cy="224" r="9" fill="#8FA3C4"/>'
           '<text x="18" y="270" fill="#9DB3D6" font-size="9" font-family="%s">SERVICE VAN · SIDE DOOR LIVERY</text>' % MONO +
           '<text x="18" y="284" fill="#5E759E" font-size="8.5" font-family="%s">01–06 wordmark · 08–17 submark · 07 delta at 0.46× oversize</text></svg>' % MONO)
    c2 = card(1, '2 · Fleet Vehicle Livery', 'pieces 01–06, 07, 08–17', van, 'Isolated glyph groups placed on a cargo door; the cobalt delta is lifted out of the A and enlarged as a standalone accent — possible only because it is its own layer.')
    # nameplate
    SC = 0.152
    np_ = ('<svg width="%s" height="300" viewBox="0 0 355 300" style="margin:0 12px;background:#06101F;border:1px solid #1E3A6E">' % f(CW-24) +
           '<rect x="8" y="20" width="339" height="200" rx="10" fill="none" stroke="#FACC15" stroke-width="1"/>'
           + ''.join('<circle cx="%d" cy="%d" r="5" fill="none" stroke="#FACC15" stroke-width="1"/>' % (x, y) for x, y in ((24, 36), (331, 36), (24, 204), (331, 204))) +
           '<g transform="translate(32,78) scale(%s) translate(-171,-179)">' % f(SC) +
           ''.join(path(c, 'none', 'stroke="#22D3EE" stroke-width="%s"' % f(1.2/SC)) for c in C if int(c['n']) <= 7) + '</g>'
           '<g transform="translate(%s,138) scale(%s) translate(-338,-491)">' % (f(32 + (338-171)*SC), f(SC)) +
           ''.join(path(c, 'none', 'stroke="#22D3EE" stroke-width="%s"' % f(1.2/SC)) for c in C if int(c['n']) >= 8) + '</g>'
           '<line x1="32" y1="62" x2="%s" y2="62" stroke="#F472B6" stroke-width=".8"/><text x="%s" y="57" text-anchor="middle" fill="#F472B6" font-size="8.5" font-family="%s">290.0 u</text>' % (f(32+1907*SC), f(32+1907*SC/2), MONO) +
           '<text x="14" y="248" fill="#22D3EE" font-size="8.5" font-family="%s">■ GLYPH_CUT  LINE ×130 + SPLINE ×31 (deg-3)</text>' % MONO +
           '<text x="14" y="262" fill="#FACC15" font-size="8.5" font-family="%s">■ PLATE_OUTLINE / MOUNT_HOLES Ø5</text>' % MONO +
           '<text x="14" y="276" fill="#5E759E" font-size="8.5" font-family="%s">KESWA_CAD_Ready.dxf · unitless px → set scale on import</text></svg>' % MONO)
    c3 = card(2, '3 · CNC / Laser Nameplate', '.DXF line + spline proof', np_, 'The shipped KESWA_CAD_Ready.dxf holds exact LINE and degree-3 SPLINE entities on 17 named layers — each glyph is a cuttable contour, not an image trace. Plate outline and holes above are illustrative layout only.')
    # spec
    fmts = [('.AI (CC)', 'KESWA_Master_Layered.ai', 'AI-layer PostScript · 17 named layers'), ('.SVG', 'KESWA_Master_Layered_Light / Dark.svg', '+ 17 individual_svgs/'),
            ('.EPS', 'KESWA_Vector_Master.eps', 'Outlined · print / sign shops'), ('.DXF', 'KESWA_CAD_Ready.dxf', 'LINE + deg-3 SPLINE · CNC / laser'),
            ('.PDF', 'KESWA_Vector_Layered.pdf', 'Vector, no embedded raster'), ('.PNG', 'KESWA_Transparent_Light/Dark_3840px.png', '3840 px wide · transparent · light + dark')]
    rows = ''.join('<tr><td class="f">%s</td><td>%s<small>%s</small></td></tr>' % (a, b, c) for a, b, c in fmts)
    spec = ('<div style="margin:0 12px;height:300px;border:1px solid #1E3A6E;background:#0B1628;padding:10px 12px"><table class="spec">%s</table>'
            '<div class="chips"><span>100%% OUTLINED SHAPES</span><span>ZERO LIVE TYPE</span><span>17 NAMED LAYERS</span><span>LIGHT + DARK</span></div></div>' % rows)
    c4 = card(3, '4 · Deliverable Spec Card', '6 formats', spec, 'Every format is generated from the same 17 closed paths, so layers, colours (#252A2D / #0043C2 · reversed #FFFFFF / #0052FF) and geometry match across files.')
    css = """
.bc{position:absolute;background:rgba(13,24,44,.95);border:1px solid #1E3A6E;border-radius:6px;overflow:hidden}
.bh{height:44px;display:flex;flex-direction:column;justify-content:center;padding:0 12px;border-bottom:1px solid #1E3A6E;margin-bottom:12px}
.bh b{font:800 13px %(sans)s;color:#fff}.bh span{font:700 9.5px %(mono)s;color:#5B9BFF;letter-spacing:.08em;text-transform:uppercase;margin-top:2px}
.bcap{font:500 11.5px/1.55 %(sans)s;color:#9DB3D6;padding:14px 14px 0}
.spec{width:100%%;border-collapse:collapse}.spec td{padding:6px 4px;border-bottom:1px solid #1B2E52;font:700 10.5px %(mono)s;color:#F1F6FF;vertical-align:top}
.spec td.f{width:68px;color:#5B9BFF;font-weight:800;font-size:12px}.spec small{display:block;color:#6F86AE;font-weight:500;font-size:9.5px;margin-top:2px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}.chips span{font:800 8.8px %(mono)s;letter-spacing:.06em;color:#CFE0FF;border:1px solid #2F6BFF;padding:4px 7px;border-radius:3px;background:#0F2347}
""" % dict(mono=MONO, sans=SANS)
    hdr = ('<div class="hdr"><div><div class="eb">Contest #2800912 · AI Image to Vector Pack · KESWA ELECTRICAL</div>'
           '<div class="tt">Sheet 02 · <b>Exploded Layers, 800%% Precision Proof</b> &amp; Modular Recombinations</div></div>'
           '<div class="rt">source: assets/source-light.png (2172 × 724)<br>%s paths · %d anchors total</div></div>' % (CURVE_WORD, sum(c['nanch'] for c in C)))
    return page('Sheet 02 · KESWA ELECTRICAL Exploded Layers & Precision Proof', css, '<div class="sheet">' + hdr + left + right + c1 + c2 + c3 + c4 + '</div>')

# =====================================================================
# index.html
# =====================================================================
def index():
    data = [dict(id=c['id'], n=c['n'], label=c['label'], group=c['group'], cl=c['color_light'], cd=c['color_dark'], d=c['d'],
                 bb=[round(v, 2) for v in c['bb']], anchors=[[round(x, 2), round(y, 2)] for x, y in c['anchors']],
                 handles=[[round(a[0], 2), round(a[1], 2), round(h[0], 2), round(h[1], 2)] for a, h in c['handles']],
                 holes=c['holes'], col=c['col']) for c in C]
    tpl = open(os.path.join(HERE, 'index.tpl.html')).read() if os.path.exists(os.path.join(HERE, 'index.tpl.html')) else None
    return INDEX_TPL.replace('__DATA__', json.dumps(data, separators=(',', ':'))).replace('__W__', str(W)).replace('__H__', str(H))

INDEX_TPL = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>KESWA ELECTRICAL · Layered Vector Asset Pack &amp; CAD Inspector</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;--sans:-apple-system,'Helvetica Neue',Helvetica,Arial,sans-serif;--blue:#5B9BFF;--line:#1E3A6E}
body{background:#070D19;color:#E6EDF7;font-family:var(--sans);padding:22px 28px 40px;min-height:100vh}
.ws{max-width:1400px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;border-bottom:1px solid var(--line);padding-bottom:14px;flex-wrap:wrap}
.eb{font:700 10.5px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--blue)}
h1{font:800 22px var(--sans);color:#fff;margin-top:4px}h1 b{color:var(--blue)}
.dl{display:flex;gap:6px;flex-wrap:wrap}
.dl a,.btn{font:800 10.5px var(--mono);color:#E6EDF7;text-decoration:none;border:1px solid #2A4577;background:#0F1D38;padding:8px 11px;border-radius:5px;cursor:pointer}
.dl a:hover,.btn:hover{border-color:var(--blue)}.dl a.pri{background:#2F6BFF;border-color:#2F6BFF;color:#fff}
.dl a.na{opacity:.4;pointer-events:none;text-decoration:line-through}
.btn.on{background:#2F6BFF;border-color:#2F6BFF;color:#fff}
.grid{display:grid;grid-template-columns:1fr 360px;gap:16px;margin-top:16px}
.pn{background:#0D182C;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.ph{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--line);font:800 10.5px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:#CFE0FF;flex-wrap:wrap}
.tools{display:flex;gap:6px;flex-wrap:wrap}.tools .btn{padding:5px 9px}
#stage{width:100%;aspect-ratio:3/1.18;display:block;transition:background .2s}
.st-light{background:#fff}.st-dark{background:#04070D}
.readout{padding:10px 12px;border-top:1px solid var(--line);font:600 11px var(--mono);color:#9DB3D6;min-height:42px;display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.readout b{color:#fff}
.layers{max-height:540px;overflow:auto}
.lr{display:flex;align-items:center;gap:8px;padding:7px 12px;border-bottom:1px solid #14264A;cursor:pointer;font:700 11px var(--mono)}
.lr:hover{background:#12254A}.lr.sel{background:#173063;box-shadow:inset 3px 0 0 var(--blue)}
.lr i{width:9px;height:9px;display:block;flex:none}.lr em{font-style:normal;color:#6F86AE;margin-left:auto;font-size:10px}
.lr a{color:var(--blue);text-decoration:none;font-size:10px;margin-left:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:12px}
.cd{background:#0A1426;border:1px solid var(--line);border-radius:5px;cursor:pointer;overflow:hidden}
.cd.sel{border-color:#5B9BFF;box-shadow:0 0 0 1px #5B9BFF}
.cd svg{display:block;width:100%;height:96px;background:#EEF2F6}
.cd div{padding:6px 8px;font:600 9.5px var(--mono);color:#9DB3D6;line-height:1.5}.cd div b{display:block;color:#F1F6FF;font-size:10px;word-break:break-all}
.cd a{color:var(--blue);text-decoration:none;font-weight:800}
.vp{pointer-events:all;cursor:pointer;transition:opacity .15s}
.note{margin-top:14px;font:500 11px/1.6 var(--sans);color:#6F86AE}
@media(max-width:980px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="ws">
<header class="top"><div><div class="eb">Contest #2800912 · AI Image to Vector Pack · KESWA ELECTRICAL</div>
<h1>17 Individually Selectable <b>Vector Layers</b> · Live Inspector</h1></div>
<div class="dl" id="dl"></div></header>
<div class="grid"><section class="pn"><div class="ph"><span>Layer Map · click any piece</span>
<div class="tools"><button class="btn on" data-m="light" id="bL">Light</button><button class="btn" data-m="dark" id="bD">Dark Reversed</button>
<button class="btn" id="bW" title="Ctrl+Y">Ctrl+Y Wireframe</button><button class="btn" id="bN">Anchor Nodes</button><button class="btn" id="bC">Clear</button></div></div>
<svg id="stage" class="st-light" viewBox="110 130 1990 500" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="readout" id="ro">Select a layer from the stage, the list or the asset grid. Shortcut: Ctrl+Y toggles wireframe.</div></section>
<aside class="pn"><div class="ph"><span>Illustrator CC Layer Stack</span><span style="color:#5B9BFF">17 / 17</span></div><div class="layers" id="ll"></div></aside></div>
<section class="pn" style="margin-top:16px"><div class="ph"><span>Modular Asset Library · 17 Closed Outlined Paths</span><span style="color:#5B9BFF">0 live type</span></div><div class="cards" id="cards"></div></section>
<p class="note">Every piece is a closed, fully outlined path on its own named layer; light master #252A2D + #0043C2, dark reversed #FFFFFF + #0052FF. Individual SVGs download from <code>exports/individual_svgs/</code>.</p>
</div>
<script>
const DATA=__DATA__, NS='http://www.w3.org/2000/svg', VB=[110,130,1990,500];
const $=s=>document.querySelector(s);
let mode='light',wire=false,nodes=false,sel=null;
const stage=$('#stage'),sc=stage.getBoundingClientRect().width?1:1;
const E=(t,a={},h='')=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(h)e.innerHTML=h;return e};
function px(){return VB[2]/(stage.getBoundingClientRect().width||1000)}
function draw(){
  stage.innerHTML='';const u=px();
  DATA.forEach(c=>{
    const g=E('g',{class:'vp','data-id':c.id});
    g.style.opacity=(sel&&sel!==c.id)?(wire?.25:.16):1;
    const fill=mode==='light'?c.cl:c.cd;
    const stroke=mode==='light'?'#111':'#fff';
    g.appendChild(E('path',{d:c.d,'fill-rule':'evenodd',fill:wire?'none':fill,stroke:wire?(mode==='light'?'#0B5FFF':'#5B9BFF'):'none','stroke-width':1.4*u}));
    if(nodes||(wire&&sel===c.id)){
      const s=5*u;
      c.handles.forEach(h=>{g.appendChild(E('line',{x1:h[0],y1:h[1],x2:h[2],y2:h[3],stroke:c.col,'stroke-width':1*u}));g.appendChild(E('circle',{cx:h[2],cy:h[3],r:s*.55,fill:c.col}))});
      c.anchors.forEach(p=>g.appendChild(E('rect',{x:p[0]-s/2,y:p[1]-s/2,width:s,height:s,fill:mode==='light'?'#fff':'#04070D',stroke:c.col,'stroke-width':1.2*u})));
    }
    if(sel===c.id){
      const [x0,y0,x1,y1]=c.bb,p=8,hs=7*u;
      g.appendChild(E('rect',{x:x0-p,y:y0-p,width:x1-x0+2*p,height:y1-y0+2*p,fill:'none',stroke:'#2F6BFF','stroke-width':1.5*u,'stroke-dasharray':(5*u)+' '+(3*u)}));
      [x0-p,(x0+x1)/2,x1+p].forEach(hx=>[y0-p,(y0+y1)/2,y1+p].forEach(hy=>{if(hx===(x0+x1)/2&&hy===(y0+y1)/2)return;g.appendChild(E('rect',{x:hx-hs/2,y:hy-hs/2,width:hs,height:hs,fill:'#fff',stroke:'#2F6BFF','stroke-width':1.2*u}))}));
    }
    g.addEventListener('click',()=>pick(c.id));
    stage.appendChild(g);
  });
}
function info(){
  const c=DATA.find(x=>x.id===sel),ro=$('#ro');
  if(!c){ro.innerHTML='Select a layer from the stage, the list or the asset grid. Shortcut: Ctrl+Y toggles wireframe.';return}
  const [x0,y0,x1,y1]=c.bb;
  ro.innerHTML='<span><b>'+c.id+'</b></span><span>'+c.group+'</span><span>'+c.anchors.length+' anchors'+(c.handles.length?' · '+c.handles.length/2+' cubic seg.':' · straight segments')+(c.holes?' · '+c.holes+' hole(s)':'')+'</span><span>'+Math.round(x1-x0)+' × '+Math.round(y1-y0)+' u</span><span>'+(mode==='light'?c.cl:c.cd)+'</span><a class="btn" href="exports/individual_svgs/'+c.id+'.svg" download>↓ SVG</a><a class="btn" href="exports/individual_pngs/'+c.id+'_'+(mode==='light'?'Light':'Dark')+'.png" download>↓ PNG</a>';
}
function pick(id){sel=(sel===id?null:id);if(sel&&!wire&&false){};render()}
function render(){draw();info();
  document.querySelectorAll('.lr,.cd').forEach(e=>e.classList.toggle('sel',e.dataset.id===sel));}
// list + cards
$('#ll').innerHTML=DATA.map(c=>'<div class="lr" data-id="'+c.id+'"><i style="background:'+c.col+'"></i>'+c.id+'<em>'+c.anchors.length+' pts</em><a href="exports/individual_svgs/'+c.id+'.svg" download onclick="event.stopPropagation()">SVG↓</a><a href="exports/individual_pngs/'+c.id+'_Light.png" download onclick="event.stopPropagation()">PNG↓</a></div>').join('');
$('#cards').innerHTML=DATA.map(c=>{const [x0,y0,x1,y1]=c.bb,p=14;return '<div class="cd" data-id="'+c.id+'"><svg viewBox="'+(x0-p)+' '+(y0-p)+' '+(x1-x0+2*p)+' '+(y1-y0+2*p)+'" preserveAspectRatio="xMidYMid meet"><path d="'+c.d+'" fill="'+c.cl+'" fill-rule="evenodd"/></svg><div><b>'+c.id+'</b>Closed Path · Outlined<br>'+c.anchors.length+' anchors · <a href="exports/individual_svgs/'+c.id+'.svg" download onclick="event.stopPropagation()">SVG ↓</a></div></div>'}).join('');
document.querySelectorAll('.lr,.cd').forEach(e=>e.addEventListener('click',()=>pick(e.dataset.id)));
function setMode(m){mode=m;stage.className.baseVal='st-'+m;$('#bL').classList.toggle('on',m==='light');$('#bD').classList.toggle('on',m==='dark');render()}
$('#bL').onclick=()=>setMode('light');$('#bD').onclick=()=>setMode('dark');
function setWire(v){wire=v;$('#bW').classList.toggle('on',wire);render()}
$('#bW').onclick=()=>setWire(!wire);
$('#bN').onclick=()=>{nodes=!nodes;$('#bN').classList.toggle('on',nodes);render()};
$('#bC').onclick=()=>{sel=null;render()};
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key.toLowerCase()==='y'){e.preventDefault();setWire(!wire)}});
window.addEventListener('resize',render);
// downloads
const FILES=[['.AI (CC)','exports/KESWA_Master_Layered.ai'],['.SVG Light','exports/KESWA_Master_Layered_Light.svg'],['.SVG Dark','exports/KESWA_Master_Layered_Dark.svg'],['.EPS','exports/KESWA_Vector_Master.eps'],['.DXF','exports/KESWA_CAD_Ready.dxf'],['.PDF','exports/KESWA_Vector_Layered.pdf'],['.PNG 3840','exports/KESWA_Transparent_Light_3840px.png'],['.PNG Dark','exports/KESWA_Transparent_Dark_3840px.png'],['↓ ALL (.ZIP)','exports/KESWA_Vector_Asset_Pack.zip']];
$('#dl').innerHTML=FILES.map((f,i)=>'<a '+(i===FILES.length-1?'class="pri" ':'')+'href="'+f[1]+'" download>'+f[0]+'</a>').join('');
if(location.protocol.startsWith('http'))document.querySelectorAll('#dl a').forEach(a=>fetch(a.getAttribute('href'),{method:'HEAD'}).then(r=>{if(!r.ok)a.classList.add('na')}).catch(()=>{}));
render();
</script></body></html>
"""

if __name__ == '__main__':
    open(os.path.join(HERE, 'board1-claude.html'), 'w').write(board1())
    open(os.path.join(HERE, 'board2-claude.html'), 'w').write(board2())
    open(os.path.join(HERE, 'index.html'), 'w').write(index())
    print('ok; cubic segments in data:', TOTAL_CUBIC)
