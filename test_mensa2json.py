#!/usr/bin/env python
# coding: utf-8

import os.path
import unittest

import mensa2json

import pdfminer.layout

TEST_DIR = os.path.join(os.path.dirname(__file__), 'testdata')

class IntegrationTest(unittest.TestCase):
    def test_integration(self):
        testFn = os.path.join(TEST_DIR, 'plan.pdf')
        with open(testFn, 'rb') as testf:
            res = mensa2json.mensa2json(testf)
        for i,dayName in enumerate(['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']):
            self.assertEquals(res[i]['dayName'], dayName)

        friday = res[4]
        self.assertEquals(friday['dayName'], 'Freitag')
        self.assertTrue(any('Fischfilet Orly' in meal['desc'] for meal in friday['meals']))
        aktion = next(meal for meal in friday['meals'] if 'Senf' in meal['desc'])
        self.assertTrue('Pommes frites' in aktion['desc'])
        self.assertEquals(aktion['priceStud'], u'2,75 €')
        self.assertEquals(aktion['priceBed'], u'3,95 €')

        # Test second page
        gratin = next(meal for meal in friday['meals'] if 'Lasagne' in meal['desc'])
        self.assertTrue('Hackfleischsauce' in gratin['desc'])
        self.assertEquals(gratin['priceStud'], u'3,35 €')
        self.assertEquals(gratin['priceBed'], u'4,55 €')

    def test_analyze_pages(self):
        testFn = os.path.join(TEST_DIR, 'plan.pdf')
        with open(testFn, 'rb') as testf:
            objs = mensa2json.analyze_pages(mensa2json.parsePDF(testf))
            texts = filter(mensa2json.accept_text, objs[pdfminer.layout.LTTextLineHorizontal])
            beilagenauswahl = next(o for o in texts if u'Beilagenauswahl' in o.get_text())
            pfanne = next(o for o in texts if u'Pfanne' in o.get_text())
            wok = next(o for o in texts if u'Wok' in o.get_text())
            greencorner = next(o for o in texts if u'Green Corner' in o.get_text())

            # per-page
            assert beilagenauswahl.ey0 > pfanne.ey0
            assert beilagenauswahl.ey1 > pfanne.ey1
            assert wok.ey0 > greencorner.ey0
            assert wok.ey1 > greencorner.ey1

            assert beilagenauswahl.ey0 > wok.ey0
            assert beilagenauswahl.ey0 > greencorner.ey0
            assert pfanne.ey0 > wok.ey0
            assert pfanne.ey0 > greencorner.ey0

    def test_make_table(self):
        testFn = os.path.join(TEST_DIR, 'plan.pdf')
        with open(testFn, 'rb') as testf:
            objs = mensa2json.analyze_pages(mensa2json.parsePDF(testf))
            texts = filter(mensa2json.accept_text, objs[pdfminer.layout.LTTextLineHorizontal])
            t = mensa2json.make_table(texts)

            # First Column
            assert u'Essen I' in t[0][0].get_text()
            assert u'Hauptkomponente' in t[0][1].get_text()
            assert u'Essen II' in t[0][2].get_text()
            assert u'Hauptkomponente' in t[0][3].get_text()
            assert u'Beilagenauswahl' in t[0][4].get_text()
            assert u'Essen I und II' in t[0][5].get_text()
            assert u'Eintöpfe' in t[0][6].get_text()
            assert u'Pfanne' in t[0][7].get_text()
            assert u'Aktionsstand' in t[0][8].get_text()
            assert u'Wok' in t[0][9].get_text()
            assert u'Gratin' in t[0][10].get_text()

            # Upper-most text (~= first row)
            assert u'Essen I' in t[0][0].get_text()
            assert u'Montag' in t[1][0].get_text()
            assert u'Dienstag' in t[2][0].get_text()
            assert u'Mittwoch' in t[3][0].get_text()
            assert u'Donnerstag' in t[4][0].get_text()
            assert u'Freitag ' in t[5][0].get_text()


if __name__ == '__main__':
    unittest.main()

# TODO test date
