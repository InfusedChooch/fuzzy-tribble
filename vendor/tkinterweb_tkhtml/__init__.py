"""
TkinterWeb-Tkhtml v1.0
This package provides pre-built binaries of a modified version of the Tkhtml3 widget from http://tkhtml.tcl.tk/tkhtml.html, 
which enables the display of styled HTML and CSS code in Tkinter applications.

This package can be used to import the Tkhtml widget into Tkinter projects
but is mainly intended to be used through TkinterWeb, which provides a full Python interface. 
See https://github.com/Andereoo/TkinterWeb.

Copyright (c) 2025 Andereoo
"""

import os




__title__ = 'TkinterWeb-Tkhtml'
__author__ = "Andereoo"
__copyright__ = "Copyright (c) 2025 Andereoo"
__license__ = "MIT"
__version__ = '1.0'


TKHTML_RELEASE = "3.0 (TkinterWeb standard)" # For debugging; eventually this project might also bundle experimental binaries
TKHTML_ROOT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "tkhtml")

tkhtml_loaded = False


def get_tkhtml_folder():
    "Get the location of the platform's Tkhtml binary"
    
    return TKHTML_ROOT_DIR


def load_tkhtml(master, location=None, force=False):
    "Load Tkhtml into the current Tcl/Tk instance"
    global tkhtml_loaded
    if (not tkhtml_loaded) or force:
        if location:
            master.tk.eval("set auto_path [linsert $auto_path 0 {" + location + "}]")
        master.tk.eval("package require Tkhtml")
        tkhtml_loaded = True