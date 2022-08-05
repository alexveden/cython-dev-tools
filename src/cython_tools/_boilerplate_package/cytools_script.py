#!/usr/bin/env python
import sys

sys.path.append('/home/ubertrader/cloud/code/cython_tools/src')

from cython_tools.cytools import main

if __name__ == '__main__':
    main(sys.argv[1:])