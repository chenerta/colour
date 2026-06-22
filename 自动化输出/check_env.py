# -*- coding: utf-8 -*-
import sys
print("Python:", sys.version)
try:
    import fitz
    print("PyMuPDF:", fitz.__version__)
except ImportError:
    print("PyMuPDF: NOT INSTALLED")
try:
    from PIL import Image
    print("Pillow: OK")
except ImportError:
    print("Pillow: NOT INSTALLED")
