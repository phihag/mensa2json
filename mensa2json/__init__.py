#!/usr/bin/env python
# coding: utf-8

import collections
import optparse
import re
import time

from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
import pdfminer.layout

_DAYS = { # time.strptime("%w")
    'Montag': '1',
    'Dienstag': '2',
    'Mittwoch': '3',
    'Donnerstag': '4',
    'Freitag': '5',
}

def parsePDF(f):
    parser = PDFParser(f)
    doc = PDFDocument()
    parser.set_document(doc)
    doc.set_parser(parser)
    doc.initialize('')

    rsrcmgr = PDFResourceManager()
    device = PDFDevice(rsrcmgr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    from pdfminer.layout import LAParams
    from pdfminer.converter import PDFPageAggregator

    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for pobj in doc.get_pages():
        interpreter.process_page(pobj)
        yield device.get_result()

def accept_text(textObj):
    t = textObj.get_text()
    _IGNORED = [u'Wochenkarte  \n', u'Mensa ', u'Bitte beachten Sie die separate Information zur Lebensmittelkennzeichnung',
        u'je 100g', u'Stud.: 0,70 €', u'Bed.:  0,80 €',]
    if t.startswith(tuple(_IGNORED)):
        return False
    if re.match(r'^[0-9\s]*$', t):
        return False
    return True

def analyze_objects(page):
    res = collections.defaultdict(list)
    q = collections.deque([page])
    while q:
        obj = q.popleft()
        res[type(obj)].append(obj)
        for c in getattr(obj, '_objs', []):
            q.append(c)
    return res

def analyze_pages(pages):
    objs = {}
    yoffset = 0
    for page in pages:
        page_objs = analyze_objects(page)
        pages = page_objs[pdfminer.layout.LTPage]
        assert len(pages) == 1
        page_size = (pages[0].y1 - pages[0].y0)
        for objs_of_type in page_objs.values():
            for o in objs_of_type:
                if hasattr(o, 'y0'):
                    o.ey0 = o.y0 + yoffset
                    o.ey1 = o.y1 + yoffset
        yoffset -= page_size

        for t,objs_of_type in page_objs.items():
            objs.setdefault(t, []).extend(objs_of_type)
    return objs

def cell2text(cell):
    return u''.join(c.get_text() for c in cell).strip()

def meal_repr(name, product_str):
    res = {'name': name}
    m = re.match(ur'^(?P<desc>.*?)(Stud\.:\s*(?P<priceStud>.*?\u20ac)\s*Bed\.:\s*(?P<priceBed>.*?\u20ac)\s*)?$', product_str, re.DOTALL)
    if m.group('priceStud'):
        res['priceStud'] = m.group('priceStud')
    if m.group('priceBed'):
        res['priceBed'] = m.group('priceBed')
    res['desc'] = m.group('desc').strip()
    return res

def mensa2json(f):
    objs = analyze_pages(parsePDF(f))

    texts = filter(accept_text, objs[pdfminer.layout.LTTextLineHorizontal])
    table = make_table(texts)
    left = min(el.x0 for el in table[0])

    lines = objs[pdfminer.layout.LTRect]
    dividers = sorted((l.ey0 for l in lines if abs(l.ey0 - l.ey1) < 1 and abs(l.x0 - left) < 5), reverse=True)
    grid = order_in_grid(table, dividers)

    match_cw = re.compile(ur'Mensa.*, (?P<calendar_week>[0-9]{1,2})\. KW[:;].*?\.(?P<year>2[0-9]{3})\s*$')
    date_data = next(
        match_cw.match(t.get_text())
        for t in objs[pdfminer.layout.LTTextLineHorizontal]
        if match_cw.match(t.get_text())
    )

    res = []
    meals = grid[0][1:]
    for col in grid[1:]:
        dayName = cell2text(col[0])
        dayStr = date_data.group('year') + ' ' + date_data.group('calendar_week') + ' ' + _DAYS[dayName]
        day = time.strptime(dayStr, '%Y %W %w')
        mealsAtDay = []
        for meal,cell in zip(meals, col[1:]):
            mealName = cell2text(meal[:1])
            if mealName == '':
                mealName = 'mensaVital'
            mealsAtDay.append(meal_repr(mealName, cell2text(cell)))
        res.append({
            'dayName': dayName,
            'date': time.strftime('%Y-%m-%d', day),
            'meals': mealsAtDay,
        })
    return res

def order_in_grid(table, dividers):
    grid = []
    for col in table:
        grid_col = [[] for _ in dividers]
        for el in col:
            grid_idx = next(i for i,y in enumerate(dividers) if el.ey0 > y)
            grid_col[grid_idx].append(el)
        grid.append(grid_col)
    return grid


def make_table(texts):
    columns = collections.defaultdict(list)
    for t in texts:
        try:
            closest_x = next(x for x in columns.keys() if abs(t.x0 - x) < 10)
        except StopIteration:
            closest_x = t.x0
        columns[closest_x].append(t)
    return [sorted(c, key=lambda t:t.ey0, reverse=True) for colIdx,c in sorted(columns.items())]

def main():
    parser = optparse.OptionParser('%prog plan.pdf')
    opts,args = parser.parse_args()

    if len(args) != 1:
        parser.error('No filename specified')
    filename = args[0]

    with open(filename, 'rb') as f:
        res = mensa2json(f)
    print(res)

if __name__ == '__main__':
    main()

# TODO web intf
# TODO .. and querying from stw
# TODO .... and caching that
# TODO .. with HTML representation
# TODO replace mensaVital graphic instead of editing the text
# TODO CLI interface
