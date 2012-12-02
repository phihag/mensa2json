#!/usr/bin/env python

import sys

if __package__ is None:
    import os.path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mensa2json

if __name__ == '__main__':
    mensa2json.main()
