"""Helpers om in Robins Google-Docs-export (.docx) te werken door bestaande elementen te klonen."""
import copy, re
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
NS = {'w': W, 'a': A, 'wp': WP, 'r': R}


def q(t):
    return '{%s}%s' % (W, t)


def clean(el):
    for e in el.iter():
        for k in list(e.attrib):
            if k.startswith('{%s}' % W14):
                del e.attrib[k]
    return el


def clone(el):
    return clean(copy.deepcopy(el))


def text_of(el):
    return ''.join(t.text or '' for t in el.iter(q('t')))


def mk_run(text, bold=False, color=None, sz=None, italic=False, underline=False):
    r = etree.Element(q('r'))
    rp = etree.SubElement(r, q('rPr'))
    if bold:
        etree.SubElement(rp, q('b')).set(q('val'), '1')
    if italic:
        etree.SubElement(rp, q('i')).set(q('val'), '1')
    if color:
        etree.SubElement(rp, q('color')).set(q('val'), color)
    if sz:
        etree.SubElement(rp, q('sz')).set(q('val'), str(sz))
        etree.SubElement(rp, q('szCs')).set(q('val'), str(sz))
    if underline:
        etree.SubElement(rp, q('u')).set(q('val'), 'single')
    _fill_run(r, text)
    return r


def _fill_run(r, text):
    for c in list(r):
        if c.tag in (q('t'), q('br'), q('tab')):
            r.remove(c)
    parts = text.split('\n')
    for i, part in enumerate(parts):
        if i:
            etree.SubElement(r, q('br'))
        t = etree.SubElement(r, q('t'))
        t.text = part
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')


def set_par_text(p, text):
    """Zet tekst in de eerste tekstrun en verwijdert de andere tekstruns (stijl van de eerste run blijft)."""
    runs = [r for r in p.iter(q('r')) if r.find(q('t')) is not None or r.find(q('br')) is not None]
    if not runs:
        runs = [r for r in p.iter(q('r')) if r.find('.//' + q('drawing')) is None]
    if not runs:
        r = etree.SubElement(p, q('r'))
        runs = [r]
    _fill_run(runs[0], text)
    for r in runs[1:]:
        r.getparent().remove(r)
    return p


def set_par_runs(p, runs):
    """Vervangt alle tekstruns door een lijst mk_run(...)-runs."""
    for r in list(p.iter(q('r'))):
        if r.find('.//' + q('drawing')) is None:
            r.getparent().remove(r)
    for h in list(p.iter(q('hyperlink'))):
        h.getparent().remove(h)
    for r in runs:
        p.append(r)
    return p


def replace_in(el, old, new):
    """Vervang tekst binnen paragrafen. Eerst per w:t, anders op paragraafniveau (samenvoegen in eerste t)."""
    n = 0
    for p in el.iter(q('p')):
        ts = list(p.iter(q('t')))
        done = False
        for t in ts:
            if t.text and old in t.text:
                t.text = t.text.replace(old, new)
                n += 1
                done = True
        if not done:
            joined = ''.join(t.text or '' for t in ts)
            if old in joined:
                ts[0].text = joined.replace(old, new)
                ts[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                for t in ts[1:]:
                    t.text = ''
                n += 1
    return n
