"""Bouwt 'Geschiedenis 1A Op onderzoek met Noor' om tot een volledige bundel (max 60 p.).
Werkt IN de Google-Docs-export: bestaande pagina's blijven, nieuwe pagina's zijn klonen van Robins eigen bouwstenen."""
import sys, re, copy
from lxml import etree
sys.path.insert(0, sys.path[0])
from lib import *

SRC = sys.argv[1]   # pad naar word/document.xml van de Google Docs-export (origineel)
DST = sys.argv[2]

tree = etree.parse(SRC)
body = tree.getroot().find(q('body'))
orig = list(body)
T = {k: copy.deepcopy(orig[i]) for k, i in dict(
    PB=23, HDR=24, TITLE=25, LABEL=26, BRON_LWB=27, NOOR=28, SP=29, IMG=30, ONTH=32,
    Q=34, PLAIN=36, LINE=57, SELF=40, TBL=54, SP80=55, EXTRA=113, HULP=136, BRON_PEL=597,
).items()}
assert text_of(orig[597]).startswith('BRONBASIS'), text_of(orig[597])
LVL = {1: 'rId7', 2: 'rId13', 3: 'rId23', 4: 'rId48', 5: 'rId80'}

# ---------------------------------------------------------------- bouwstenen

def PB(): return clone(T['PB'])
def SP(): return clone(T['SP'])
def SP80(): return clone(T['SP80'])

def HDR(text):
    t = clone(T['HDR']); set_par_text(t.find('.//' + q('p')), text); return t

def TITLE(text):
    return set_par_text(clone(T['TITLE']), text)

def LABEL(text, lvl=3, color=None):
    p = clone(T['LABEL'])
    runs = [r for r in p.iter(q('r')) if r.find(q('t')) is not None]
    runs[0].find(q('t')).text = text
    if color:
        runs[0].find(q('rPr')).find(q('color')).set(q('val'), color)
    p.find('.//{%s}blip' % A).set('{%s}embed' % R, LVL[lvl])
    return p

def BRON(text, kind=None, werkvorm=None):
    """kind: None = geen link, 'lwb' of 'pel' = link van het origineel behouden."""
    p = clone(T['BRON_PEL'] if kind == 'pel' else T['BRON_LWB'])
    h = p.find('.//' + q('hyperlink'))
    if kind is None:
        inner = clone(h.find(q('r')))
        h.getparent().replace(h, inner)
        inner.find(q('t')).text = text
        inner.find(q('rPr')).remove(inner.find(q('rPr')).find(q('u')))
    else:
        h.find('.//' + q('t')).text = text
    if werkvorm:
        add_werkvorm(p, werkvorm)
    return p

def add_werkvorm(p, werkvorm):
    p.append(mk_run('   |   WERKVORM   ', bold=True, color='61747b', sz=18))
    p.append(mk_run(werkvorm, bold=True, color='EE7D22', sz=18))

def BOX(kind, title, paras):
    """kind: noor (turquoise), onth (groen), extra (rood V+)."""
    b = clone(T[{'noor': 'NOOR', 'onth': 'ONTH', 'extra': 'EXTRA'}[kind]])
    tc = b.find('.//' + q('tc'))
    ps = tc.findall(q('p'))
    set_par_text(ps[0], title)
    tpl = ps[1]
    for p in ps[1:]:
        tc.remove(p)
    for txt in paras:
        np_ = clone(tpl)
        for h in list(np_.iter(q('hyperlink'))):
            h.getparent().remove(h)
        if isinstance(txt, list):
            set_par_runs(np_, txt)
        else:
            set_par_text(np_, txt)
        tc.append(np_)
    return b

def Qp(text):
    return set_par_text(clone(T['Q']), text)

def PLAIN(text, runs=None):
    p = clone(T['PLAIN'])
    if runs:
        return set_par_runs(p, runs)
    return set_par_text(p, text)

def LINES(n):
    return [clone(T['LINE']) for _ in range(n)]

def SELF():
    return clone(T['SELF'])

def HULP(text):
    return set_par_text(clone(T['HULP']), text)

def IMG(rid, w_cm, h_cm, caption):
    t = clone(T['IMG'])
    d = t.find('.//' + q('drawing'))
    d.find('.//{%s}blip' % A).set('{%s}embed' % R, rid)
    cx, cy = str(int(w_cm * 360000)), str(int(h_cm * 360000))
    for e in d.iter('{%s}extent' % WP, '{%s}ext' % A):
        if e.get('cx') is not None:
            e.set('cx', cx); e.set('cy', cy)
    ps = t.findall('.//' + q('p'))
    set_par_text(ps[-1], caption)
    return t

def _shd(tc, fill):
    tcPr = tc.find(q('tcPr'))
    s = tcPr.find(q('shd'))
    if s is None:
        s = etree.Element(q('shd')); s.set(q('val'), 'clear')
        bd = tcPr.find(q('tcBorders'))
        (bd.addnext(s) if bd is not None else tcPr.insert(0, s))
    s.set(q('fill'), fill)

def TABLE(widths, header, rows, row_h=595, fills=None, header_fill=None, bold_first_col=False,
          sz=None, center_cols=()):
    """widths in twips (som 9978). header: lijst teksten of None. rows: lijst rijen; cel = str of lijst runs."""
    src = T['TBL']
    tbl = etree.Element(q('tbl'))
    tbl.append(clone(src.find(q('tblPr'))))
    grid = etree.SubElement(tbl, q('tblGrid'))
    for w in widths:
        etree.SubElement(grid, q('gridCol')).set(q('w'), str(w))
    trs = src.findall(q('tr'))
    htc, btc = trs[0].find(q('tc')), trs[1].find(q('tc'))
    def mkrow(cells, head, ri):
        tr = etree.SubElement(tbl, q('tr'))
        trPr = clone((trs[0] if head else trs[1]).find(q('trPr')))
        th = trPr.find(q('trHeight'))
        if not head:
            if row_h is None and th is not None:
                trPr.remove(th)
            elif th is not None:
                th.set(q('val'), str(row_h))
        tr.append(trPr)
        for ci, cell in enumerate(cells):
            tc = clone(htc if head else btc)
            tcPr = tc.find(q('tcPr'))
            tcW = etree.Element(q('tcW')); tcW.set(q('w'), str(widths[ci])); tcW.set(q('type'), 'dxa')
            tcPr.insert(0, tcW)
            if head and header_fill:
                _shd(tc, header_fill)
            if not head and fills and (ri, ci) in fills:
                _shd(tc, fills[(ri, ci)])
            p = tc.find(q('p'))
            if ci in center_cols:
                pPr = p.find(q('pPr'))
                jc = etree.Element(q('jc')); jc.set(q('val'), 'center')
                rp_ = pPr.find(q('rPr'))
                (rp_.addprevious(jc) if rp_ is not None else pPr.append(jc))
            if isinstance(cell, list):
                set_par_runs(p, cell)
            else:
                if head:
                    set_par_text(p, cell)
                else:
                    set_par_runs(p, [mk_run(cell, bold=(bold_first_col and ci == 0), sz=sz)])
            tr.append(tc)
    if header:
        mkrow(header, True, -1)
    for ri, r in enumerate(rows):
        mkrow(r, False, ri)
    return tbl

def R_(text, **kw):
    return mk_run(text, **kw)

GREY = '61747b'; TURQ = '009BA8'; ORANJE = 'EE7D22'; ROOD = 'E61149'; DGROEN = '47701b'
FILL_T, FILL_G, FILL_R, FILL_HEAD = 'edf8fa', 'f2f7e8', 'fdeeeb', 'eaf3d5'


def page(*items):
    out = [PB()]
    for it in items:
        for el in (it if isinstance(it, list) else [it]):
            if el.tag == q('tbl') and out[-1].tag == q('tbl') and len(out) > 2:
                out.append(SP())
            out.append(el)
    return out

# ---------------------------------------------------------------- originele pagina's opsplitsen
pages = []
cur = []
sect = orig[-1]
for el in orig[:-1]:
    if el.tag == q('p') and el.xpath('w:pPr/w:pageBreakBefore[not(@w:val="0")]', namespaces=NS):
        pages.append(cur); cur = [el]
    else:
        cur.append(el)
pages.append(cur)

def ptitle(pg):
    for el in pg[1:4]:
        if el.tag == q('p') and text_of(el).strip():
            return text_of(el).strip()
    return text_of(pg[1]) if len(pg) > 1 else ''

byt = {ptitle(pg): pg for pg in pages[2:]}
cover, route = pages[0], pages[1]

def P(title):
    return byt[title]

# ---------------------------------------------------------------- p. 2: route
# route[0]=PB,1=hdr,2=title,3=noor box,4=sp,5=tabel,6=sp,7=onthoud,8=sp,9=SO-zin,10=LWB-zin
route_new = route[:5]
noorbox = route[3]
tc = noorbox.find('.//' + q('tc'))
for p in tc.findall(q('p'))[1:-1]:
    tc.remove(p)
ROUTE = [
    ('Leeswijzer: zo werk je met deze bundel', 'leeswijzer', None),
    ('Hoofdstuk 1: Werken met geschiedenis (doelen en start)', 'h1open', None),
    ('Les 1: wat is geschiedenis? Archeoloog, historicus en tijdvakken • SO1', 'l1a', 'l1b'),
    ('Les 2: historische vragen, bronnen, ruimte en 4 domeinen • SO2', 'l2a', 'l2b'),
    ('Syntheseschema H1 • verdiepend brononderzoek (V+)', 'syn1', 'vplus1'),
    ('Hoofdstuk 2: Het historisch referentiekader (doelen en start)', 'h2open', None),
    ('Les 3: het referentiekader, van jaartal naar eeuw', 'l3a', 'l3b'),
    ('Les 4: kaart, domeinen, alles situeren • SO3 • codekraker', 'l4a', 'code'),
    ('Syntheseschema H2', 'syn2', None),
    ('Hoofdstuk 3: Prehistorie (doelen en start)', 'h3open', None),
    ('Les 5: instap, aanpassen of uitsterven', 'l5', None),
    ('Les 6: OV1, visies op de oorsprong van de mens', 'l6a', 'l6b'),
    ('Les 7: OV2, omgeving, Lucy en Laetoli', 'l7a', 'laetoli'),
    ('Les 8: OV2, werktuigen, vuur, feiten en hypotheses', 'l8a', 'l8b'),
    ('Les 9: OV3, verspreiding van Homo sapiens • tijdlijnspel', 'l9a', 'tijdlijn'),
    ('Les 10: museumtekst • syntheseschema H3 • klaar voor de BT', 'l10a', 'l10b'),
    ('Les 11: begrippen, hulpkaarten en remediëring', 'begrip', 'wod'),
    ('Les 12: oefenexamen en verrijking', 'exa', 'vplus2'),
    ('Portfolio en beeldverantwoording', 'portfolio', 'beeld'),
]
rows = []
for txt, a, b in ROUTE:
    rows.append([txt, '{{P:%s}}' % a + ('-{{P:%s}}' % b if b else '')])
route_tbl = TABLE([8300, 1678], ['Les en tussenstop', 'Bundelpagina'], rows, row_h=None, center_cols=(1,))
route_new = route[:5] + [route_tbl, SP80(),
    PLAIN('', runs=[R_('Tip: ', bold=True, color=TURQ), R_('lees eerst de leeswijzer op p. {{P:leeswijzer}}. Daar staat wat elk kader, label en icoon betekent.')])]

# ---------------------------------------------------------------- p. 3: leeswijzer
lw_rows = [
    [[R_('NOOR ONDERZOEKT', bold=True, color=TURQ)], 'Een kort verhaal met een probleem. De vraag van Noor is ook jouw onderzoeksvraag.'],
    [[R_('BRONBASIS', bold=True, color=GREY)], 'Waar je de leerstof terugvindt. LWB = je leerwerkboek. Pelckmans = hoofdstuk 3, p. 28-43.'],
    [[R_('Bron, Kaart, Schema', bold=True)], 'Elk beeld heeft een nummer en een bijschrift. Verwijs ernaar in je antwoord: "In bron 4 zie ik ..."'],
    [[R_('ONTHOUD', bold=True, color='94C021')], 'De leerstof die je moet kennen voor de SO en de BT.'],
    [[R_('a  b  c', bold=True)], 'De opdrachten. Lees eerst het werkwoord: noteer, kruis aan, leg uit, vergelijk.'],
    [[R_('Rotsblokjes 1-5', bold=True)], '1 = herkennen, 3 = toepassen, 5 = zelfstandig bronnen afwegen.'],
    [[R_('WERKVORM', bold=True, color=ORANJE)], 'Hoe je werkt: ALLEEN, DUO, GROEP of KLAS. Wacht op het startsein van je leerkracht.'],
    [[R_('Zelfcheck', bold=True, color=GREY)], 'Kruis eerlijk aan of je het zelf kan. Noteer je volgende stap.'],
]
sp_rows = [
    [[R_('BASIS', bold=True, color=TURQ)], 'Label BASIS, ONTHOUD-kaders', 'Iedereen. Dit is de route van de klas.'],
    [[R_('REMEDIËRING', bold=True, color=ORANJE)], 'Label REMEDIËRING, HULP-regels, woordbanken, hulpkaarten p. {{P:hulptijd}}-{{P:wod}}', 'Wie vastloopt of na een SO extra wil oefenen.'],
    [[R_('VERRIJKING V+', bold=True, color=ROOD)], 'Rood kader V+, label VERRIJKING', 'Wie de basis zelfstandig beheerst.'],
]
leeswijzer = page(
    HDR('Start   |   Leeswijzer'), TITLE('Zo werk je met deze bundel'),
    BOX('noor', 'ZO ZIET EEN PAGINA ERUIT', ['Elke pagina is één onderzoeksstap. Bovenaan zie je in welk hoofdstuk en welke les je zit. Daarna volgen altijd dezelfde bouwstenen, in dezelfde volgorde.']),
    SP(), TABLE([2600, 7378], ['Bouwsteen', 'Wat doe je ermee?'], lw_rows, row_h=None),
    SP(), IMG('rId80', 6.0, 0.7, 'Rotsblokjes: hoe meer donkere blokjes, hoe moeilijker de oefening.'),
    SP(), PLAIN('', runs=[R_('Drie sporen', bold=True, color=TURQ, sz=24)]),
    TABLE([2400, 4000, 3578], ['Spoor', 'Herken je aan', 'Voor wie?'], sp_rows, row_h=None,
          fills={(0, 0): FILL_T, (1, 0): FILL_G, (2, 0): FILL_R}),
    SP(),
    PLAIN('SO1, SO2 en SO3 zijn oefentussenstops in deze bundel. Je leerkracht spreekt de echte toetsdatum af. Een lesblok kan meer dan één lesuur vragen. Deze bundel heeft een eigen paginanummering.'),
)

# ---------------------------------------------------------------- hoofdstukopeningen
def doelen(rows):
    return TABLE([1900, 8078], ['Les', 'Na deze les kan ik ...'],
                 [[[R_(a, bold=True, color=TURQ)], b] for a, b in rows], row_h=None)

h1open = page(
    HDR('H1 Werken met geschiedenis   |   Hoofdstukopening'), TITLE('Hoofdstuk 1: Werken met geschiedenis'),
    IMG('rId15', 7.6, 4.0, 'Bron 4 • Opgraving. Zo werkt een archeoloog. Je onderzoekt deze foto op p. {{P:l1a+2}}.'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Noor scrolt langs een filmpje over het Groot Egyptisch Museum in Caïro, dat eind 2025 helemaal de deuren opende. "Hoe weten ze eigenlijk hoe oud al die dingen zijn?" vraagt ze. Tante Lies lacht: "Niet door te raden. Door vragen te stellen en sporen te onderzoeken. Dat ga jij ook leren."']),
    SP(),
    BOX('noor', 'ONZE ONDERZOEKSVRAAG', [[R_('Hoe onderzoekt een historicus het verleden van de mens?', bold=True)]]),
    SP(),
    doelen([
        ('Les 1', 'uitleggen wat geschiedenis is • geschreven en ongeschreven bronnen onderscheiden • het werk van een archeoloog en een historicus vergelijken • de zeven tijdvakken in volgorde noemen en een jaartal in het juiste tijdvak plaatsen'),
        ('Les 2', 'een historische vraag herkennen en scherper maken • ruimte en schaal benoemen, van lokaal tot mondiaal • de vier maatschappelijke domeinen uitleggen en toepassen • zeggen of een bron bruikbaar is voor mijn vraag'),
    ]),
    SP(),
    Qp('START   Mindmap in duo: wat betekent geschiedenis voor jou? Schrijf minstens zes woorden rond het middelpunt. Omcirkel daarna samen het woord dat jullie het belangrijkst vinden.'),
    TABLE([3326, 3326, 3326], None, [['', '', ''], ['', [R_('GESCHIEDENIS', bold=True, color='FFFFFF', sz=24)], ''], ['', '', '']],
          row_h=700, fills={(1, 1): TURQ}, center_cols=(1,)),
)

h2open = page(
    HDR('H2 Historisch referentiekader   |   Hoofdstukopening'), TITLE('Hoofdstuk 2: Het historisch referentiekader'),
    IMG('rId20', 2.6, 3.2, 'Bron 10 • Griekse vaas, ca. 530 v.C. Je situeert ze op p. {{P:l3a}}.'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Lies stuurt drie vondstkaartjes. Op elk kaartje staat maar één woord: OUD. "Daar heb ik niets aan", zucht Noor. "Hoe oud? Waar gevonden? En wat vertelt het over het leven van mensen?" Lies knikt. "Met tijd, ruimte en domein maak je van oud een echt antwoord."']),
    SP(),
    BOX('noor', 'ONZE ONDERZOEKSVRAAG', [[R_('Hoe situeer je een vondst precies in tijd, ruimte en maatschappij?', bold=True)]]),
    SP(),
    doelen([
        ('Les 3', 'uitleggen wat het historisch referentiekader is • een jaartal omzetten naar een eeuw, ook voor Christus • een eeuw en een tijdvak niet verwarren'),
        ('Les 4', 'landen en plaatsen op een kaart van Europa terugvinden en windrichtingen gebruiken • een vondst aan het juiste domein koppelen en dat uitleggen • tijd, ruimte en domein samen gebruiken bij één vondst'),
    ]),
    SP(),
    Qp('START   Vier hoeken (KLAS). Elke hoek van het lokaal is een domein: economisch, politiek, sociaal en cultureel. Je leerkracht leest een situatie voor. Ga in de passende hoek staan en leg je keuze uit met omdat.'),
    TABLE([6000, 1989, 1989], ['Situatie', 'Mijn hoek', 'Na het gesprek'], [
        ['1  Een bakker in Bree verhoogt de prijs van brood.', '', ''],
        ['2  De gemeenteraad beslist over een nieuw fietspad.', '', ''],
        ['3  Jongeren ontmoeten elkaar in de jeugdbeweging.', '', ''],
        ['4  Een museum toont een nieuw kunstwerk.', '', ''],
        ['5  Een fabriek sluit en veel mensen verliezen hun werk.', '', ''],
    ], row_h=420),
)

h3open = page(
    HDR('H3 Prehistorie   |   Hoofdstukopening'), TITLE('Hoofdstuk 3: Prehistorie'),
    IMG('rId58', 2.3, 3.45, 'Bron 13 • Gereconstrueerd skelet van Lucy. Je onderzoekt het op p. {{P:lucy0}}.'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Lies werkt bij een opgraving in Tanzania. Ze stuurt Noor een spraakbericht: "Hier zoeken we sporen van mensen van miljoenen jaren geleden. Geen brieven, geen boeken. Alleen botten, stenen en voetsporen." Noor vraagt zich af: hoe kun je dan iets zeker weten?']),
    SP(),
    BOX('noor', 'ONZE ONDERZOEKSVRAGEN', [
        [R_('OV1  ', bold=True, color=TURQ), R_('Welke visies zijn er over de oorsprong van de mens? (les 6)')],
        [R_('OV2  ', bold=True, color=TURQ), R_('Waardoor is de mens mens geworden? (les 7 en 8)')],
        [R_('OV3  ', bold=True, color=TURQ), R_('Wat waren de gevolgen van de verspreiding van de mens over de wereld? (les 9)')],
    ]),
    SP(),
    doelen([
        ('Les 5-6', 'uitleggen wat prehistorie is • creationisme en evolutietheorie onderscheiden en respectvol bespreken • uitleggen wat een fossiel en een reconstructie zijn'),
        ('Les 7-8', 'uitleggen hoe natuurlijke selectie werkt • aanwijzingen voor rechtop lopen bij Lucy en in Laetoli noemen • ontwikkelingen met gevolgen verbinden • een vaststelling van een hypothese onderscheiden'),
        ('Les 9-10', 'de verspreiding van Homo sapiens op een kaart tonen • gevolgen van die verspreiding uitleggen • een kort besluit schrijven met bewijs en onzekerheid'),
    ]),
    SP(),
    Qp('START   Eens of oneens? Kruis aan wat jij nu denkt. In les 10 (p. {{P:l10b}}) kijk je opnieuw: veranderde je mening?'),
    TABLE([6378, 900, 900, 900, 900], ['Stelling', 'Nu eens', 'Nu oneens', 'Later eens', 'Later oneens'], [
        ['1  De mens stamt af van de chimpansee die vandaag leeft.', '[ ]', '[ ]', '[ ]', '[ ]'],
        ['2  Een fossiel vertelt ons alles over een wezen van vroeger.', '[ ]', '[ ]', '[ ]', '[ ]'],
        ['3  Alle mensen die vandaag leven, behoren tot dezelfde soort.', '[ ]', '[ ]', '[ ]', '[ ]'],
        ['4  Er leefden ooit verschillende mensensoorten tegelijk.', '[ ]', '[ ]', '[ ]', '[ ]'],
    ], row_h=None, center_cols=(1, 2, 3, 4)),
)

# ---------------------------------------------------------------- synthese H1 + V+
syn1 = page(
    HDR('H1 Werken met geschiedenis   |   Synthese'), TITLE('Syntheseschema: zo onderzoekt een historicus'),
    LABEL('OEFENING 00   |   BASIS + REMEDIËRING   |   ', 3),
    BRON('p. {{P:l1a}}-{{P:l2b}} van deze bundel', werkvorm='ALLEEN, daarna DUO'),
    IMG('rId26', 14.0, 3.08, 'Schema 2 • Van een vraag naar een onderbouwd antwoord (zie ook p. {{P:l2a}}).'),
    SP(),
    TABLE([2494, 2494, 2495, 2495], [
        [R_('1  VRAAG  →', bold=True, color=TURQ)], [R_('2  BRONNEN  →', bold=True, color=TURQ)],
        [R_('3  SITUEREN  →', bold=True, color=TURQ)], [R_('4  ANTWOORD', bold=True, color=TURQ)]], [
        ['Een historische vraag gaat over het verleden van (1) ............ .\n\nZe is onderzoekbaar met (2) ............ en duidelijk in tijd, ruimte en onderwerp.',
         'Geschreven bron: ............\n\nOngeschreven bron: ............\n\nEen archeoloog onderzoekt materiële (3) ............ .',
         'Tijd: tijdvak en eeuw.\n\nRuimte: van (4) ............ tot mondiaal.\n\nDomein: economisch, (5) ............, (6) ............, cultureel.',
         'Een goed antwoord steunt op (7) ............ uit bronnen.\n\nHet zegt ook wat we (8) ............ weten.'],
    ], row_h=3200, sz=20),
    SP(),
    BOX('onth', 'HULP   WOORDBANK (REMEDIËRING)', ['mensen  •  bronnen  •  sporen  •  lokaal  •  politiek  •  sociaal  •  bewijs  •  niet']),
    SP(),
    Qp('a  Vul het syntheseschema aan. Lukt het niet zonder hulp? Gebruik de woordbank.'),
    Qp('b  Vul de zeven tijdvakken van oud naar jong aan zonder terug te bladeren.'),
    TABLE([1425] * 6 + [1428], None, [['Prehistorie', '', '', '', '', '', '']], row_h=600, sz=18),
    SP(),
    Qp('c  Leg het schema in één minuut uit aan je buur. Je buur vinkt af: vraag [ ]  bronnen [ ]  situeren [ ]  antwoord [ ]'),
    SP(), SELF(),
)

vplus1 = page(
    HDR('H1 Werken met geschiedenis   |   Verrijking'), TITLE('Verdiepend brononderzoek: de vuistbijl uit Meeuwen'),
    LABEL('OEFENING 00   |   VERRIJKING V+   |   ', 5),
    BRON('LWB p. 12-13 en 18', kind='lwb', werkvorm='ALLEEN'),
    BOX('extra', 'V+   ONDERZOEKSVRAAG', [
        [R_('Wat vertelt de vuistbijl uit Meeuwen ons over hoe mensen in onze streek aan voedsel kwamen?', bold=True)],
        [R_('Denkwoorden:  ', bold=True), R_('bron  •  bruikbaar  •  betrouwbaar  •  wat we niet weten', color=ROOD, bold=True)]]),
    SP(),
    IMG('rId9', 2.0, 3.0, 'Bron 1 • Vuistbijl uit Meeuwen, ca. 112 000-40 000 jaar geleden. Foto uit het LWB p. 18. Meeuwen ligt op een paar kilometer van Bree.'),
    SP(),
    TABLE([4300, 5678], ['Stap', 'Mijn antwoord'], [
        [[R_('1  CONTEXT', bold=True), R_('  Wat is het? Waar gevonden? Hoe oud?')], ''],
        [[R_('2  BRUIKBAAR?', bold=True), R_('  Helpt de bron bij de onderzoeksvraag? Ja of nee, want ...')], ''],
        [[R_('3  WAARNEMEN', bold=True), R_('  Noteer twee dingen die je aan het voorwerp zelf ziet.')], ''],
        [[R_('4  GRENZEN', bold=True), R_('  Noteer twee dingen die deze bron niet vertelt.')], ''],
        [[R_('5  BETROUWBAAR?', bold=True), R_('  Wie bepaalde de ouderdom? Waarom vertrouw je dat meer dan een gok?')], ''],
        [[R_('6  ANTWOORD', bold=True), R_('  Beantwoord de onderzoeksvraag in twee zinnen.')], ''],
    ], row_h=820, fills={(i, 0): FILL_R for i in range(6)}),
    SP(),
    PLAIN('', runs=[R_('Besluit: streep door wat niet past. ', bold=True),
                    R_('De vuistbijl is een geschreven / ongeschreven bron. Ze is bruikbaar / niet bruikbaar voor mijn vraag. Ze bewijst wel / niet wie de maker precies was. Om zekerder te zijn, vergelijk ik met één / meerdere bronnen.')]),
    SP(), SELF(),
)

# ---------------------------------------------------------------- codekraker + synthese H2
def opt(*opts):
    runs = []
    for i, (letter, txt) in enumerate(opts):
        if i:
            runs.append(R_('     '))
        runs.append(R_(letter + ' ', bold=True, color=ROOD))
        runs.append(R_(txt))
    return runs

code = page(
    HDR('H2 Historisch referentiekader   |   Les 4'), TITLE('Codekraker: open het museumdepot'),
    LABEL('OEFENING 00   |   BASIS   |   ', 3),
    BRON('p. {{P:tijdvakken}} en p. {{P:l3a}}-{{P:l4b}} van deze bundel', werkvorm='DUO, elk een eigen blad'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Het depot van het museum zit op slot. De code is een woord van acht letters. Elk juist antwoord geeft je één letter. Omcirkel per vraag het juiste antwoord en noteer de letter. Pas als alle acht letters kloppen, gaat de deur open.']),
    SP(),
    TABLE([500, 3900, 4778, 800], ['Nr', 'Vraag', 'Omcirkel', 'Letter'], [
        ['1', 'In welk tijdvak hoort het jaar 1939?', opt(('K', 'hedendaagse tijd'), ('T', 'moderne tijd'), ('M', 'vroegmoderne tijd')), ''],
        ['2', 'In welke eeuw ligt het jaar 1200?', opt(('E', '11de eeuw'), ('A', '13de eeuw'), ('O', '12de eeuw')), ''],
        ['3', 'Een onderzoek over de markt van Bree. Welke schaal?', opt(('R', 'nationaal'), ('N', 'lokaal'), ('S', 'mondiaal')), ''],
        ['4', 'Wie heeft macht en welke regels gelden? Welk domein?', opt(('L', 'sociaal'), ('D', 'economisch'), ('G', 'politiek')), ''],
        ['5', 'In welke eeuw ligt 530 v.C.?', opt(('E', '6de eeuw v.C.'), ('I', '5de eeuw v.C.'), ('U', '53ste eeuw v.C.')), ''],
        ['6', 'Een boer verkoopt graan op de markt. Welk domein?', opt(('B', 'cultureel'), ('R', 'economisch'), ('P', 'politiek')), ''],
        ['7', 'Wat is het eerste jaar van de 21ste eeuw?', opt(('O', '2000'), ('A', '2100'), ('E', '2001')), ''],
        ['8', 'In welk werelddeel ligt Tanzania?', opt(('Z', 'Azië'), ('N', 'Afrika'), ('V', 'Europa')), ''],
    ], row_h=520, center_cols=(0, 3)),
    SP(),
    Qp('a  Noteer de letters in volgorde. Dit is de code:'),
    TABLE([1247] * 7 + [1249], [str(i) for i in range(1, 9)], [[''] * 8], row_h=650, center_cols=tuple(range(8))),
    SP(),
    Qp('b  Controle: de code is de naam van een Limburgse stad met een bekend Gallo-Romeins museum. Klopt je woord niet? Zoek bij welk vraagnummer het misliep.'),
    Qp('c  Kies één vraag die je eerst fout had. Leg uit wat je nu anders doet.'),
    LINES(2), SP(), SELF(),
)

syn2 = page(
    HDR('H2 Historisch referentiekader   |   Synthese'), TITLE('Syntheseschema: het historisch referentiekader'),
    LABEL('OEFENING 00   |   BASIS + REMEDIËRING   |   ', 3),
    BRON('LWB p. 14-28', kind='lwb', werkvorm='ALLEEN, daarna DUO'),
    IMG('rId43', 13.0, 3.45, 'Schema 4 • Eeuwen na Christus (zie p. {{P:eeuwen}}).'),
    SP(),
    TABLE([1900, 2692, 2693, 2693], ['', [R_('TIJD', bold=True, color=TURQ)], [R_('RUIMTE', bold=True, color=TURQ)], [R_('MAATSCHAPPIJ', bold=True, color=TURQ)]], [
        [[R_('Kernvraag', bold=True)], 'Wanneer?', 'Waar?', 'Welke kant van het leven?'],
        [[R_('Hulpmiddel', bold=True)], 'jaartal → eeuw → (1) ............', 'kaart, werelddeel, windrichting en schaal: lokaal, (2) ............, nationaal, continentaal, mondiaal', 'vier domeinen: economisch, politiek, (3) ............, (4) ............'],
        [[R_('Valkuil', bold=True)], '1900 ligt in de (5) ............ eeuw, niet in de 20ste.', 'Huidige landsgrenzen bestonden in de prehistorie (6) ............ .', 'Het domein hangt af van de (7) ............ die je stelt.'],
        [[R_('Mijn voorbeeld', bold=True)], '', '', ''],
    ], row_h=900, sz=20, fills={(i, 0): FILL_HEAD for i in range(4)}),
    SP(),
    BOX('onth', 'HULP   WOORDBANK (REMEDIËRING)', ['tijdvak  •  regionaal  •  sociaal  •  cultureel  •  19de  •  nog niet  •  vraag']),
    SP(),
    Qp('a  Vul het syntheseschema aan. Schrijf in de laatste rij telkens een eigen voorbeeld.'),
    Qp('b  Situeer: een Romeinse munt uit de 2de eeuw, gevonden in Tongeren. Je onderzoekt de handel in die stad.'),
    TABLE([2494, 2494, 2495, 2495], ['Tijdvak', 'Werelddeel', 'Schaal', 'Domein'], [['', '', '', '']], row_h=600),
    SP(),
    Qp('c  Vergelijk met je buur. Waar verschillen jullie antwoorden? Wie onderbouwt het best?'),
    SP(), SELF(),
)

# ---------------------------------------------------------------- tijdlijnspel + synthese H3
def kaart(letter, txt, when):
    return [R_(letter + '  ', bold=True, color=ROOD), R_(txt + '\n'), R_(when, bold=True, color=TURQ)]

tijdlijn = page(
    HDR('H3 Prehistorie   |   Les 9   |   OV3: Gevolgen van de verspreiding'), TITLE('Tijdlijnspel: wanneer leefden ze, wanneer vonden we ze?'),
    LABEL('OEFENING 00   |   BASIS   |   ', 3),
    BRON('Pelckmans p. 30-35', kind='pel', werkvorm='DUO: kaartjes leggen'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Noor legt de kaartjes van Lies op tafel. Er liggen twee soorten jaartallen door elkaar: wanneer iets leefde of gebeurde, en wanneer onderzoekers het ontdekten. "Als je die twee verwart, klopt je hele tijdlijn niet", zegt Lies.']),
    SP(),
    TABLE([2494, 2494, 2495, 2495], None, [
        [kaart('A', 'Voetsporen in Laetoli worden gemaakt', 'ca. 3,6 miljoen jaar geleden'),
         kaart('B', 'Lucy leeft in het huidige Ethiopië', 'ca. 3,2 miljoen jaar geleden'),
         kaart('C', 'Homo erectus verschijnt', 'ca. 2 miljoen jaar geleden'),
         kaart('D', 'Homo sapiens ontstaat in Afrika', 'ruim 300 000 jaar geleden')],
        [kaart('E', 'Homo sapiens leeft in Europa', 'ca. 40 000 jaar geleden'),
         kaart('F', 'Onderzoekers vinden Lucy', '1974'),
         kaart('G', 'Onderzoekers vinden de voetsporen van Laetoli', '1978'),
         kaart('H', 'Einde van de prehistorie in de schoolindeling', 'ca. 3500 v.C.')],
    ], row_h=1000, sz=20),
    SP(),
    Qp('a  Verdeel de kaartjes in twee groepen. Noteer de letters.'),
    TABLE([4989, 4989], ['LEEFDE OF GEBEURDE', 'ONTDEKT DOOR ONDERZOEKERS'], [['', '']], row_h=600),
    SP(),
    Qp('b  Zet de kaartjes uit de groep LEEFDE OF GEBEURDE van oud naar jong.'),
    TABLE([1663] * 5 + [1663], ['oudst', '', '', '', '', 'jongst'], [[''] * 6], row_h=600, center_cols=tuple(range(6))),
    SP(),
    Qp('c  Rekenopdracht: op je tijdlijn is 1 meter gelijk aan 4 miljoen jaar. Hoeveel cm vóór vandaag ligt kaartje D? En kaartje E?'),
    LINES(1),
    HULP('HULP   4 miljoen jaar = 100 cm, dus 40 000 jaar = 1 cm.'),
    Qp('d  Wat valt je op? Leg in één zin uit waarom de prehistorie het langste tijdvak is.'),
    LINES(2), SP(), SELF(),
)

syn3 = page(
    HDR('H3 Prehistorie   |   Les 10'), TITLE('Syntheseschema: prehistorie'),
    LABEL('OEFENING 00   |   BASIS + REMEDIËRING   |   ', 3),
    BRON('Pelckmans p. 28-43', kind='pel', werkvorm='ALLEEN, daarna DUO'),
    IMG('rId70', 8.6, 4.5, 'Kaart 3 • Verspreiding van Homo sapiens, sterk vereenvoudigd (zie p. {{P:l9a}}).'),
    SP(),
    TABLE([1900, 2692, 2693, 2693], ['', [R_('OV1  Visies', bold=True, color=TURQ)], [R_('OV2  Mens worden', bold=True, color=TURQ)], [R_('OV3  Verspreiding', bold=True, color=TURQ)]], [
        [[R_('Kernbegrippen', bold=True)], 'creationisme • evolutietheorie • fossiel • reconstructie', 'natuurlijke selectie • rechtop lopen • werktuigen • vuur', 'migratie • Homo sapiens • variatie'],
        [[R_('Bewijs', bold=True)], 'Lucy leefde ca. (1) ............ jaar geleden.', 'Voetsporen in (2) ............, ca. 3,6 miljoen jaar oud.', 'Homo sapiens ontstond in (3) ............ en leefde ca. (4) ............ jaar geleden in Europa.'],
        [[R_('Let op', bold=True)], 'Evolutie gebeurt over vele (5) ............, niet in één leven.', 'Een tekening rond het vuur is geen (6) ............ uit de prehistorie.', 'Alle mensen vandaag zijn één soort.'],
        [[R_('Mijn antwoord in één zin', bold=True)], '', '', ''],
    ], row_h=900, sz=20, fills={(i, 0): FILL_HEAD for i in range(4)}),
    SP(),
    BOX('onth', 'HULP   WOORDBANK (REMEDIËRING)', ['3,2 miljoen  •  Laetoli  •  Afrika  •  40 000  •  generaties  •  bron']),
    SP(),
    Qp('a  Vul het schema aan. Schrijf in de laatste rij per onderzoeksvraag een antwoord van één zin.'),
    Qp('b  Maak een keten van oorzaak en gevolg: rechtop lopen → ............................ → ............................'),
    Qp('c  Duo: de ene legt OV1 en OV2 uit met het schema, de andere OV3. Noem bij elk antwoord één bron.'),
    SP(), SELF(),
)

# ---------------------------------------------------------------- wat ontdekten we (R)
wod = page(
    HDR('Extra steun   |   Les 11'), TITLE('Wat ontdekten we? Prehistorie in een notendop'),
    LABEL('OEFENING 00   |   REMEDIËRING   |   ', 1, color=ORANJE),
    BRON('p. {{P:l6a}}-{{P:l9b}} van deze bundel', werkvorm='ALLEEN'),
    BOX('noor', 'NOOR ONDERZOEKT', ['Noor vat haar ontdekkingen samen voor de schoolkrant. Ze laat de belangrijkste woorden open zodat haar klasgenoten kunnen oefenen. Jij vult aan.']),
    SP(),
    BOX('onth', 'WOORDBANK', ['Afrika  •  as  •  evolutietheorie  •  fossielen  •  generaties  •  Homo sapiens  •  hypothese  •  Lucy  •  migratie  •  reconstructie  •  schepper  •  vuur']),
    SP(),
    IMG('rId77', 6.5, 3.4, 'Kaart 4 • Hadar in Ethiopië en Laetoli in Tanzania (zie p. {{P:l10a}}).'),
    SP(),
    Qp('a  Vul de tekst aan met de woorden uit de woordbank. Elk woord gebruik je één keer.'),
    PLAIN('', runs=[R_('OV1  ', bold=True, color=TURQ), R_('Over de oorsprong van de mens bestaan verschillende visies. Bij creationisme staat een (1) ............ centraal. De (2) ............ is een wetenschappelijke verklaring: levende wezens veranderen over vele (3) ............ . Onderzoekers gebruiken onder meer (4) ............ als bewijs. Een skelet in een museum is vaak een (5) ............ : ontbrekende stukken zijn aangevuld.')]),
    SP(),
    PLAIN('', runs=[R_('OV2  ', bold=True, color=TURQ), R_('(6) ............ leefde ca. 3,2 miljoen jaar geleden in Ethiopië. Haar bekken wijst op rechtop lopen. In Laetoli bleven voetsporen bewaard in vochtige vulkanische (7) ............ . Werktuigen en (8) ............ veranderden wat mensen konden. Een mogelijke verklaring die we nog moeten toetsen, noemen we een (9) ............ .')]),
    SP(),
    PLAIN('', runs=[R_('OV3  ', bold=True, color=TURQ), R_('(10) ............ ontstond ruim 300 000 jaar geleden in (11) ............ . Door (12) ............ verspreidden groepen zich over de wereld. Alle mensen die vandaag leven, behoren tot dezelfde soort.')]),
    SP(),
    Qp('b  Markeer in de tekst: geel = tijd, blauw = ruimte, groen = bewijs.'),
    HULP('HULP   Twijfel je? Kijk terug: OV1 p. {{P:l6a}}-{{P:l6b}}, OV2 p. {{P:l7a}}-{{P:l8b}}, OV3 p. {{P:l9a}}-{{P:l9b}}. Verbeter met de aparte verbetersleutel.'),
    SP(), SELF(),
)

# ---------------------------------------------------------------- oefenexamen
def vraag(nr, txt, ptn, waar):
    return PLAIN('', runs=[R_('%s  ' % nr, bold=True, color=TURQ), R_(txt, bold=True),
                           R_('   (%s)   ' % ptn, bold=True, color=ROOD), R_(waar, color=GREY, sz=18)])

exa1 = page(
    HDR('Oefenexamen   |   Les 12'), TITLE('Oefenexamen: test jezelf'),
    LABEL('OEFENING 00   |   TEST JEZELF   |   ', 4),
    BRON('hele bundel', werkvorm='ALLEEN, zonder bladeren, 50 minuten'),
    PLAIN('', runs=[R_('Zo pak je het aan: ', bold=True, color=TURQ), R_('lees eerst je doelen op p. {{P:h1open}}, {{P:h2open}} en {{P:h3open}}. Werk zonder te bladeren. Verbeter met de verbetersleutel en noteer je score in je portfolio (p. {{P:portfolio}}).')]),
    SP(),
    vraag('1', 'Juist of fout? Verbeter de foute zinnen.', '5 ptn', '[les 1, 3, 8, 9]'),
    TABLE([6000, 700, 3278], ['Zin', 'J/F', 'Verbetering'], [
        ['a  Een foto is een ongeschreven bron.', '', ''],
        ['b  Het jaar 1900 ligt in de 20ste eeuw.', '', ''],
        ['c  Een archeoloog onderzoekt alleen geschreven bronnen.', '', ''],
        ['d  Homo sapiens ontstond in Europa.', '', ''],
        ['e  Een reconstructietekening is een foto van vroeger.', '', ''],
    ], row_h=380, center_cols=(1,)),
    SP(),
    vraag('2', 'Vul de tabel aan.', '3 ptn', '[les 1 en 3, p. {{P:tijdvakken}} en {{P:eeuwen}}]'),
    TABLE([3326, 3326, 3326], ['Jaartal', 'Eeuw', 'Tijdvak'], [['1482', '', ''], ['530 v.C.', '', ''], ['2026', '', '']], row_h=400),
    SP(),
    vraag('3', 'Koppel elke situatie aan één maatschappelijk domein.', '2 ptn', '[les 2 en 4, p. {{P:l2a+4}}]'),
    vraag('4', 'Welke schaal past bij elk onderzoek?', '2 ptn', '[les 2, p. {{P:l2a+3}}]'),
    TABLE([3500, 1489, 3500, 1489], ['Situatie (vraag 3)', 'Domein', 'Onderzoek (vraag 4)', 'Schaal'], [
        ['A  Een koning legt een nieuwe belasting op.', '', 'A  De kermis in Bree in 1950', ''],
        ['B  Mensen ruilen vuursteen voor zout.', '', 'B  De steenkoolmijnen in Limburg', ''],
        ['C  In een groep zorgen jongeren voor ouderen.', '', 'C  De verkiezingen in België in 2024', ''],
        ['D  Mensen beschilderen de wanden van een grot.', '', 'D  De verspreiding van Homo sapiens', ''],
    ], row_h=520, sz=20),
)

exa2 = page(
    HDR('Oefenexamen   |   Les 12'), TITLE('Oefenexamen: test jezelf (vervolg)'),
    vraag('5', 'Is "Hoe leefden ze vroeger?" een goede historische vraag? Maak ze scherper met tijd, ruimte en onderwerp.', '2 ptn', '[les 2, p. {{P:l2a}}-{{P:l2a+1}}]'),
    LINES(2), SP(),
    vraag('6', 'Vaststelling (V) of hypothese (H)? Noteer V of H.', '2 ptn', '[les 8, p. {{P:watweten}}]'),
    TABLE([8778, 1200], ['Uitspraak', 'V of H'], [
        ['a  In Laetoli liggen afdrukken van voeten in verharde as.', ''],
        ['b  De makers van de voetsporen waren een vader, een moeder en een kind.', ''],
        ['c  Op dezelfde plek liggen verbrande resten en stenen werktuigen.', ''],
        ['d  Rond het vuur vertelden mensen elke avond verhalen.', ''],
    ], row_h=480, center_cols=(1,)),
    SP(),
    vraag('7', 'Leg in twee zinnen uit wat natuurlijke selectie is. Gebruik: erfelijke verschillen, voortplanting, generaties.', '2 ptn', '[les 7, p. {{P:l7a}}]'),
    LINES(3), SP(),
    vraag('8', 'Een bezoeker zegt: "De voetsporen van Laetoli zijn 1978 jaar oud." Wat gaat er mis? Noteer de juiste ouderdom van de sporen en het jaar van de ontdekking.', '3 ptn', '[les 7, p. {{P:laetoli}}]'),
    LINES(3), SP(),
    vraag('9', 'Beantwoord OV3 in vier zinnen. Noem de oorsprong, de verspreiding en twee gevolgen.', '4 ptn', '[les 9, p. {{P:l9a}}-{{P:l9b}}]'),
    LINES(5), SP(),
    TABLE([3326, 6652], None, [
        [[R_('Mijn score', bold=True, color=TURQ)], [R_('............ / 25', bold=True)]],
        [[R_('Dit oefen ik nog', bold=True, color=TURQ)], 'vraag ............ op p. ............ en p. ............'],
    ], row_h=560, fills={(0, 0): FILL_T, (1, 0): FILL_T}),
)

# ---------------------------------------------------------------- portfolio + beeldverantwoording
portfolio = page(
    HDR('Portfolio   |   Mijn leerweg'), TITLE('Portfolio: hoe doe ik het?'),
    BOX('noor', 'ZO GEBRUIK JE DIT', ['Vul deze pagina in na elke tussenstop. Zo zien jij en je leerkracht waar je groeit. Je ik kan-lijst voor de prehistorie staat op p. {{P:l10b}}.']),
    SP(),
    TABLE([1700, 1300, 2400, 2289, 2289], ['Tussenstop', 'Score', 'Hoe voelde het?', 'Wat ging goed?', 'Wat oefen ik nog? (p.)'], [
        [[R_('SO1', bold=True)], '', 'goed • oké • moeilijk', '', ''],
        [[R_('SO2', bold=True)], '', 'goed • oké • moeilijk', '', ''],
        [[R_('SO3', bold=True)], '', 'goed • oké • moeilijk', '', ''],
        [[R_('Oefenexamen', bold=True)], '', 'goed • oké • moeilijk', '', ''],
        [[R_('BT', bold=True)], '', 'goed • oké • moeilijk', '', ''],
    ], row_h=600, sz=20),
    SP(),
    PLAIN('', runs=[R_('Ik kan-doelen hoofdstuk 1 en 2', bold=True, color=TURQ, sz=24)]),
    TABLE([6678, 1100, 1100, 1100], ['Ik kan ...', 'zelf', 'met hulp', 'nog niet'], [
        ['de zeven tijdvakken in volgorde noemen (p. {{P:tijdvakken}})', '[ ]', '[ ]', '[ ]'],
        ['geschreven en ongeschreven bronnen onderscheiden (p. {{P:l1a+1}})', '[ ]', '[ ]', '[ ]'],
        ['een goede historische vraag maken (p. {{P:l2a}}-{{P:l2a+1}})', '[ ]', '[ ]', '[ ]'],
        ['de ruimtelijke schaal benoemen (p. {{P:l2a+3}})', '[ ]', '[ ]', '[ ]'],
        ['de vier maatschappelijke domeinen toepassen (p. {{P:l2a+4}}-{{P:l2a+6}})', '[ ]', '[ ]', '[ ]'],
        ['zeggen wat een bron wel en niet bewijst (p. {{P:l2a+7}})', '[ ]', '[ ]', '[ ]'],
        ['een jaartal in een eeuw en een tijdvak plaatsen (p. {{P:eeuwen}}-{{P:l3b}})', '[ ]', '[ ]', '[ ]'],
        ['een vondst situeren in tijd, ruimte en domein (p. {{P:l4a+2}}-{{P:l4b}})', '[ ]', '[ ]', '[ ]'],
    ], row_h=None, center_cols=(1, 2, 3)),
    SP(),
    Qp('Mijn leervaardigheid: kies plannen, hulp vragen of ordelijk werken. Schrijf één concreet doel voor de volgende weken.'),
    LINES(2),
)

beeld = page(
    HDR('Naslag   |   Beeldverantwoording'), TITLE('Beeldverantwoording'),
    TABLE([1900, 1300, 6778], ['Beeld', 'Pagina', 'Aard en herkomst'], [
        ['Cover', '1', 'Illustratie bij het verzonnen verhaal van Noor en tante Lies.'],
        ['Bron 1', '{{P:l1a}}, {{P:vplus1}}', 'Vuistbijl uit Meeuwen. Foto uit het LWB p. 18.'],
        ['Bron 2-3', '{{P:l1a+1}}', 'Geschreven spoor en onderzoek van een vondst. Herkomst: [aan te vullen].'],
        ['Bron 4', '{{P:l1a+2}}, {{P:h1open}}', 'Opgraving. Herkomst: [aan te vullen].'],
        ['Schema 1', '{{P:tijdvakken}}', 'Schoolindeling in tijdvakken, naar het LWB.'],
        ['Bron 5-8', '{{P:l2a+5}}', 'Foto\'s bij de maatschappelijke domeinen. Herkomst: [aan te vullen].'],
        ['Bron 9', '{{P:l2a+6}}', 'Uniform van een jeugdbeweging, LWB p. 25.'],
        ['Bron 10-11', '{{P:l2a+7}}, {{P:l3a}}, {{P:h2open}}', 'Griekse vaas, ca. 530 v.C. Foto en datering uit het LWB p. 18.'],
        ['Kaart 1-4', '{{P:l2a+2}}, {{P:l4a}}, {{P:l9a}}, {{P:l10a}}', 'Kaartbasis Natural Earth (publiek domein), eigen bewerking.'],
        ['Bron 12, 15, 17', '{{P:l5}}, {{P:laetoli}}, {{P:vplus2}}', 'Afgietsel van de voetsporen van Laetoli. Foto: Momotarou2012, CC BY-SA 3.0.'],
        ['Bron 13-14', '{{P:lucy0}}, {{P:lucy}}, {{P:h3open}}', 'Gereconstrueerd skelet van Lucy. Foto: Chip Clark, Smithsonian Institution.'],
        ['Bron 16', '{{P:l8a}}', 'Bewerkt stenen werktuig. Herkomst: [aan te vullen].'],
        ['Schema 2-6', 'div.', 'Eigen schema\'s bij deze bundel.'],
    ], row_h=None, sz=20),
    SP(),
    PLAIN('Leerstof en informatie: leerwerkboek geschiedenis 1A (LWB), Pelckmans hoofdstuk 3 p. 28-43, Smithsonian National Museum of Natural History (humanorigins.si.edu). De gesprekken van Noor en Lies zijn verzonnen; de historische informatie en bronnen niet.'),
)

# ---------------------------------------------------------------- volgorde van de bundel
order = []
def add(key, pg):
    order.append((key, pg))

add('cover', cover)
add('route', route_new)
add('leeswijzer', leeswijzer)
add('h1open', h1open)
L1 = ['Wat is geschiedenis', 'Sporen vertellen niet alles', 'Archeoloog en historicus', 'De tijdlijn om te studeren', 'Een eerste reis door de tijd', 'Tussenstop SO1']
L2 = ['Een historicus begint met een vraag', 'Noor maakt haar vraag scherper', 'Waar ligt Noors onderzoeksplek', 'Van lokaal naar mondiaal', 'Vier kanten van het leven', 'Kijken en een domein kiezen', 'Eén voorwerp meer dan één domein', 'Niet zomaar geloven', 'Tussenstop SO2']
L3 = ['Het historisch referentiekader', 'Van jaartal naar eeuw', 'Eeuwen en tijdvakken oefenen']
L4 = ['Noor leest een kaart van Europa', 'Vondsten aan domeinen koppelen', 'Het grote vondstenonderzoek', 'TEST JEZELF SO3 - alles situeren']
L6 = ['Waar begint het verhaal van de mens', 'Evolutie is geen rechte ladder', 'Fossielen zijn aanwijzingen', 'Mijn antwoord op OV1 - Welke visies zijn er over de oorsprong van de mens?']
L7 = ['Leven in een veranderende omgeving', 'Lucy kan klimmen en lopen', 'Voetsporen lezen in Laetoli']
L8 = ['Handen werktuigen en vuur', 'Wat weten we en wat vermoeden we', 'Mijn antwoord op OV2 - Waardoor is de mens mens geworden?']
L9 = ['Mensen verspreiden zich', 'Niet alleen op de wereld', 'Eén mensensoort veel verschillen', 'Mijn antwoord op OV3 - Wat waren de gevolgen van de verspreiding van de mens over de wereld?']

HEAD = {}
for t in L1: HEAD[t] = 'H1 Werken met geschiedenis   |   Les 1'
for t in L2: HEAD[t] = 'H1 Werken met geschiedenis   |   Les 2'
for t in L3: HEAD[t] = 'H2 Historisch referentiekader   |   Les 3'
for t in L4: HEAD[t] = 'H2 Historisch referentiekader   |   Les 4'
for t in L6: HEAD[t] = 'H3 Prehistorie   |   Les 6   |   OV1: Visies op de oorsprong van de mens'
for t in L7: HEAD[t] = 'H3 Prehistorie   |   Les 7   |   OV2: Waardoor is de mens mens geworden?'
for t in L8: HEAD[t] = 'H3 Prehistorie   |   Les 8   |   OV2: Waardoor is de mens mens geworden?'
for t in L9: HEAD[t] = 'H3 Prehistorie   |   Les 9   |   OV3: Gevolgen van de verspreiding'
HEAD['Les 5 - Prehistorie: aanpassen of uitsterven'] = 'H3 Prehistorie   |   Les 5'
HEAD['Noor maakt een museumtekst'] = 'H3 Prehistorie   |   Les 10'
HEAD['Les 10 - Klaar voor de BT'] = 'H3 Prehistorie   |   Les 10'
HEAD['Les 11 - Mijn begrippenblad'] = 'Naslag   |   Les 11'
HEAD['Les 11 - Hulpkaart tijd'] = 'Extra steun   |   Les 11'
HEAD['Les 11 - Hulpkaart vragen, ruimte en domeinen'] = 'Extra steun   |   Les 11'
HEAD['Een verhaal dat te mooi klinkt'] = 'Verrijking   |   Les 12'

for i, t in enumerate(L1): add('l1a' if i == 0 else ('l1b' if i == len(L1) - 1 else t), P(t))
for i, t in enumerate(L2): add('l2a' if i == 0 else ('l2b' if i == len(L2) - 1 else t), P(t))
add('syn1', syn1); add('vplus1', vplus1); add('h2open', h2open)
for i, t in enumerate(L3): add('l3a' if i == 0 else ('l3b' if i == len(L3) - 1 else t), P(t))
for i, t in enumerate(L4): add('l4a' if i == 0 else ('l4b' if i == len(L4) - 1 else t), P(t))
add('code', code); add('syn2', syn2); add('h3open', h3open)
add('l5', P('Les 5 - Prehistorie: aanpassen of uitsterven'))
for i, t in enumerate(L6): add('l6a' if i == 0 else ('l6b' if i == len(L6) - 1 else t), P(t))
for i, t in enumerate(L7): add('l7a' if i == 0 else t, P(t))
for i, t in enumerate(L8): add('l8a' if i == 0 else ('l8b' if i == len(L8) - 1 else t), P(t))
for i, t in enumerate(L9): add('l9a' if i == 0 else ('l9b' if i == len(L9) - 1 else t), P(t))
add('tijdlijn', tijdlijn)
add('l10a', P('Noor maakt een museumtekst'))
add('syn3', syn3)
add('l10b', P('Les 10 - Klaar voor de BT'))
add('begrip', P('Les 11 - Mijn begrippenblad'))
add('hulptijd', P('Les 11 - Hulpkaart tijd'))
add('hulpvragen', P('Les 11 - Hulpkaart vragen, ruimte en domeinen'))
add('wod', wod)
add('exa', exa1); add('exa2', exa2)
add('vplus2', P('Een verhaal dat te mooi klinkt'))
add('portfolio', portfolio); add('beeld', beeld)

PAGE = {k: i + 1 for i, (k, _) in enumerate(order)}
PAGE['tijdvakken'] = PAGE['De tijdlijn om te studeren']
PAGE['eeuwen'] = PAGE['Van jaartal naar eeuw']
PAGE['lucy0'] = PAGE['Fossielen zijn aanwijzingen']
PAGE['lucy'] = PAGE['Lucy kan klimmen en lopen']
PAGE['laetoli'] = PAGE['Voetsporen lezen in Laetoli']
PAGE['watweten'] = PAGE['Wat weten we en wat vermoeden we']
PAGE['l7b'] = PAGE['laetoli']
assert len(order) <= 60, len(order)

# ---------------------------------------------------------------- correcties in bestaande pagina's
TITLEFIX = {
    'Wat is geschiedenis': 'Wat is geschiedenis?',
    'Waar ligt Noors onderzoeksplek': 'Waar ligt Noors onderzoeksplek?',
    'Eén voorwerp meer dan één domein': 'Eén voorwerp, meer dan één domein',
    'TEST JEZELF SO3 - alles situeren': 'Test jezelf SO3: alles situeren',
    'Les 5 - Prehistorie: aanpassen of uitsterven': 'Les 5: Prehistorie, aanpassen of uitsterven',
    'Waar begint het verhaal van de mens': 'Waar begint het verhaal van de mens?',
    'Mijn antwoord op OV1 - Welke visies zijn er over de oorsprong van de mens?': 'Mijn antwoord op OV1: welke visies zijn er over de oorsprong van de mens?',
    'Mijn antwoord op OV2 - Waardoor is de mens mens geworden?': 'Mijn antwoord op OV2: waardoor is de mens mens geworden?',
    'Mijn antwoord op OV3 - Wat waren de gevolgen van de verspreiding van de mens over de wereld?': 'Mijn antwoord op OV3: wat waren de gevolgen van de verspreiding van de mens over de wereld?',
    'Handen werktuigen en vuur': 'Handen, werktuigen en vuur',
    'Wat weten we en wat vermoeden we': 'Wat weten we en wat vermoeden we?',
    'Eén mensensoort veel verschillen': 'Eén mensensoort, veel verschillen',
    'Les 10 - Klaar voor de BT': 'Les 10: klaar voor de BT',
    'Les 11 - Mijn begrippenblad': 'Les 11: mijn begrippenblad',
    'Les 11 - Hulpkaart tijd': 'Les 11: hulpkaart tijd',
    'Les 11 - Hulpkaart vragen, ruimte en domeinen': 'Les 11: hulpkaart vragen, ruimte en domeinen',
}
WERKVORM = {
    'Wat is geschiedenis': 'DENKEN, DELEN, UITWISSELEN',
    'De tijdlijn om te studeren': 'DUO: overhoor elkaar',
    'Een eerste reis door de tijd': 'GROEP: tijdlijnrace',
    'Noor maakt haar vraag scherper': 'DUO: vragenruil',
    'Kijken en een domein kiezen': 'DUO: kies en verdedig',
    'Niet zomaar geloven': 'DENKEN, DELEN, UITWISSELEN',
    'Het grote vondstenonderzoek': 'GROEP VAN 3: elk één kaart, daarna uitwisselen',
    'Waar begint het verhaal van de mens': 'KLAS: respectvol klasgesprek',
    'Voetsporen lezen in Laetoli': 'DUO: bewijs of verhaal?',
    'Wat weten we en wat vermoeden we': 'KLAS: stellingenlijn',
    'Noor maakt een museumtekst': 'DUO: schrijven en feedback geven',
    'Les 10 - Klaar voor de BT': 'DUO: vertel het na',
}
TEXTFIX = [
    ('KENNEN - Definitie van geschiedenis: geschiedenis is', 'KENNEN   Definitie van geschiedenis. Geschiedenis is'),
    ('KENNEN - Een goede', 'KENNEN   Een goede'),
    ('TAAK - MUSEUMONDERZOEK', 'TAAK   MUSEUMONDERZOEK'),
    ('Noor gebruikt de tabel op p. 6.', 'Noor gebruikt de tabel op p. {{P:tijdvakken}}.'),
    ('Gebruik p. 6.', 'Gebruik p. {{P:tijdvakken}}.'),
    ('Maak p. 43 A. Controleer met p. 6. ', 'Maak p. {{P:hulptijd}} A. Controleer met p. {{P:tijdvakken}}. '),
    ('Gebruik p. 6 en 19 als', 'Gebruik p. {{P:tijdvakken}} en {{P:eeuwen}} als'),
    ('Gebruik p. 43 B voor', 'Gebruik p. {{P:hulptijd}} B voor'),
    ('Gebruik bronnen uit p. 31-34.', 'Gebruik bronnen uit p. {{P:lucy}}-{{P:watweten}}.'),
    ('Zoek de twee grenzen op p. 6.', 'Zoek de twee grenzen op p. {{P:tijdvakken}}.'),
    ('Keer terug naar p. 8 of 20.', 'Keer terug naar p. {{P:tijdvakken}} (tijdvakken) of p. {{P:eeuwen}} (eeuwen).'),
    ('Dezelfde voetsporen als op p. 32.', 'Dezelfde voetsporen als op p. {{P:laetoli}}.'),
    ('Broninformatie uit p. 32', 'Broninformatie uit p. {{P:laetoli}}'),
    ('sinds haar eerste museumbezoek?', 'sinds haar eerste museumbezoek? Kijk ook terug naar je stellingen op p. {{P:h3open}}.'),
    ('HULP   Gebruik de hulpkaart vragen, ruimte en domeinen als je vastloopt. Controleer met de aparte verbetersleutel. Oefen daarna opnieuw zonder hulp.', 'HULP   Vastgelopen? Hulpkaart op p. {{P:hulpvragen}}. Controleer met de verbetersleutel en oefen opnieuw.'),
]

for key, pg in order:
    if key in ('cover', 'route') or pg in (leeswijzer, h1open, h2open, h3open, syn1, vplus1, code, syn2, tijdlijn, syn3, wod, exa1, exa2, portfolio, beeld):
        continue
    t = ptitle(pg)
    # kopregel
    if t in HEAD:
        set_par_text(pg[1].find('.//' + q('p')), HEAD[t])
    # titel
    if t in TITLEFIX:
        for el in pg[1:4]:
            if el.tag == q('p') and text_of(el).strip() == t:
                set_par_text(el, TITLEFIX[t])
    # werkvorm bij bronbasis
    if t in WERKVORM:
        for el in pg:
            if el.tag == q('p') and text_of(el).startswith('BRONBASIS'):
                add_werkvorm(el, WERKVORM[t]); break
    for el in pg:
        for old, new in TEXTFIX:
            replace_in(el, old, new)
        # V+ verwijzing in oefening 2
        if el.tag == q('p') and text_of(el).startswith('VERRIJKING V+ - Extra in Classroom'):
            set_par_runs(el, [R_('VERRIJKING V+   ', bold=True, color=ROOD),
                              R_('Klaar met de basis? Maak het verdiepend brononderzoek over de vuistbijl uit Meeuwen op p. {{P:vplus1}}. Je vindt het ook in Classroom.', bold=True)])

# remediëringskader in groen (sporenkleur), niet in de rode verrijkingskleur
rem = orig[865]
assert text_of(rem).startswith('REMEDIËRING')
for e in rem.iter():
    if e.get(q('fill')) == 'fdeeeb': e.set(q('fill'), 'f2f7e8')
    if e.get(q('color')) == 'e85547': e.set(q('color'), '94C021')          # kaderrand
    if e.tag == q('color') and e.get(q('val')) == 'e85547': e.set(q('val'), 'EE7D22')  # titel

# SO2-pagina compacter: TAAK in één alinea
so2 = P('Tussenstop SO2')
so2.remove(orig[327]); so2.remove(orig[332]); so2.remove(orig[334])
set_par_text(orig[333], 'TAAK   Museumonderzoek Tongeren (basis, na les 2): kies een museumvoorwerp en noteer tijd, plaats, twee domeinen en drie feiten. De opdracht staat in Classroom.')

# ---------------------------------------------------------------- body opnieuw opbouwen
for el in list(body):
    body.remove(el)
for key, pg in order:
    for el in pg:
        body.append(el)
body.append(sect)

# oefeningen doorlopend nummeren
n = 0
for p in body.iter(q('p')):
    ts = list(p.iter(q('t')))
    if ts and ts[0].text and re.match(r'OEFENING \d\d', ts[0].text):
        n += 1
        ts[0].text = re.sub(r'OEFENING \d\d', 'OEFENING %02d' % n, ts[0].text, count=1)
print('oefeningen:', n, 'pagina\'s:', len(order))

# paginaverwijzingen invullen
def resolve(m):
    key = m.group(1)
    off = 0
    if '+' in key:
        key, o = key.split('+'); off = int(o)
    return str(PAGE[key] + off)
for t in body.iter(q('t')):
    if t.text and '{{P:' in t.text:
        t.text = re.sub(r'\{\{P:([^}]+)\}\}', resolve, t.text)

for pm in body.iter(q('pgMar')):
    if pm.get(q('gutter')) is None: pm.set(q('gutter'), '0')

# docPr-id's uniek maken
for i, d in enumerate(body.iter('{%s}docPr' % WP), start=1):
    d.set('id', str(i))

xml = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
# huisstijl MHH: kleuren gelijktrekken
for old, new in [('0093ba', '009BA8'), ('9acb1f', '94C021'), ('e85547', 'E61149'), ('bd4c20', 'EE7D22')]:
    xml = xml.replace(('"%s"' % old).encode(), ('"%s"' % new).encode())
open(DST, 'wb').write(xml)

import json
json.dump(PAGE, open(sys.argv[3], 'w'), indent=1, ensure_ascii=False)
