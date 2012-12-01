#!/usr/bin/env python

import collections
import re

from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
import pdfminer.layout

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
    _IGNORED = [u'Wochenkarte  \n', 'Mensa Universit', 'Bitte beachten Sie die separate Information zur Lebensmittelkennzeichnung']
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

def cell2text(cell):
    return u''.join(c.get_text() for c in cell).strip()

def meal_repr(name, product_str):
    res = {'name': name}
    #\s*Bed\\.:\s*(?P<priceBed>.*?\u20ac)\s*$
    m = re.match(ur'^(?P<desc>.*?)(Stud\.:\s*(?P<priceStud>.*?\u20ac)\s*Bed\.:\s*(?P<priceBed>.*?\u20ac)\s*)?$', product_str, re.DOTALL)
    if m.group('priceStud'):
        res['priceStud'] = m.group('priceStud')
    if m.group('priceBed'):
        res['priceBed'] = m.group('priceBed')
    res['desc'] = m.group('desc').strip()
    return res

def main():
    with open('plan.pdf', 'rb') as f:
        for page in parsePDF(f):
            objs = analyze_objects(page)
            texts = filter(accept_text, objs[pdfminer.layout.LTTextLineHorizontal])
            table = make_table(texts)
            left = min(el.x0 for el in table[0])

            lines = objs[pdfminer.layout.LTRect]
            dividers = sorted((l.y0 for l in lines if abs(l.y0 - l.y1) < 1 and abs(l.x0 - left) < 5), reverse=True)
            grid = order_in_grid(table, dividers)

            res = collections.OrderedDict()
            meals = grid[0][1:]
            for col in grid[1:]:
                dayName = cell2text(col[0])
                res[dayName] = dayEntry = []
                for meal,cell in zip(meals, col[1:]):
                    mealName = cell2text(meal[:1])
                    if mealName == '':
                        mealName = 'mensaVital'
                    dayEntry.append(meal_repr(mealName, cell2text(cell)))
            print(repr(res))
            return

def order_in_grid(table, dividers):
    grid = []
    for col in table:
        grid_col = [[] for _ in dividers]
        for el in col:
            grid_idx = next(i for i,y in enumerate(dividers) if el.y0 > y)
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
    return [sorted(c, key=lambda t:t.y0, reverse=True) for colIdx,c in sorted(columns.items())]

if __name__ == '__main__':
    main()

# TODO web intf with HTML representation
# TODO replace mensaVital graphic instead of editing the text