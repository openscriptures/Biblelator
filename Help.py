#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Help.py
#   Last modified: 2014-10-23 (also update ProgVersion below)
#
# Main program for Biblelator Bible display/editing
#
# Copyright (C) 2014 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Program to allow editing of USFM Bibles using Python3 and Tkinter.
"""

ShortProgName = "Help"
ProgName = "Help Box"
ProgVersion = "0.19"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = True


import sys #, os.path, configparser, logging
from gettext import gettext as _

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Button

from BiblelatorGlobals import MINIMUM_HELP_X_SIZE, MINIMUM_HELP_Y_SIZE, centreWindowOnWindow

sourceFolder = "../BibleOrgSys/"
sys.path.append( sourceFolder )
import Globals



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if Globals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



class HelpBox( tk.Toplevel ):
    def __init__( self, parent=None, progName=None, text=None ):
        #if Globals.debugFlag: print( "HelpBox.__init__( {} )".format( parent ) )
        tk.Toplevel.__init__( self, parent )
        self.minimumXSize, self.minimumYSize = MINIMUM_HELP_X_SIZE, MINIMUM_HELP_Y_SIZE
        self.minsize( self.minimumXSize, self.minimumYSize )
        if parent: centreWindowOnWindow( self, parent )

        self.okButton = Button( self, text='Ok', command=self.destroy )
        self.okButton.pack( side=tk.BOTTOM )

        self.title( 'Help for '+progName )
        self.textBox = ScrolledText( self ) #, state=tk.DISABLED )
        self.textBox['wrap'] = 'word'
        self.textBox.insert( tk.END, text )
        self.textBox['state'] = tk.DISABLED # Don't allow editing
        self.textBox.pack( expand=tk.YES )

        self.focus_set() # take over input focus,
        self.grab_set() # disable other windows while I'm open,
        self.wait_window() # and wait here until win destroyed
    # end of HelpBox.__init__
# end of class HelpBox


class HelpBox2():
    def __init__( self, parent=None, progName=None, text=None ):
        if Globals.debugFlag: print( "HelpBox2.__init__( {} )".format( parent ) )
        hb = tk.Toplevel( parent )
        self.minimumXSize, self.minimumYSize = MINIMUM_HELP_X_SIZE, MINIMUM_HELP_Y_SIZE
        self.minsize( self.minimumXSize, self.minimumYSize )
        if parent: centreWindowOnWindow( self, parent )

        self.okButton = Button( hb, text='Ok', command=hb.destroy )
        self.okButton.pack( side=tk.BOTTOM )

        hb.title( 'Help for '+progName )
        textBox = ScrolledText( hb ) #, state=tk.DISABLED )
        textBox['wrap'] = 'word'
        textBox.pack( expand=tk.YES )
        textBox.insert( tk.END, text )
        textBox['state'] = tk.DISABLED # Don't allow editing

        hb.focus_set() # take over input focus,
        hb.grab_set() # disable other windows while I'm open,
        hb.wait_window() # and wait here until win destroyed
    # end of HelpBox.__init__
# end of class HelpBox


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )
    #if Globals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    print( "Running demo..." )
    #Globals.debugFlag = True

    tkRootWindow = tk.Tk()
    tkRootWindow.title( ProgNameVersion )
    ab = HelpBox( tkRootWindow, ProgName, ProgNameVersion )
    ab = HelpBox2( tkRootWindow, ProgName, ProgNameVersion )
    # Calls to the window manager class (wm in Tk)
    #tkRootWindow.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()
# end of main


if __name__ == '__main__':
    import multiprocessing

    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables


    if Globals.debugFlag:
        from tkinter import tix
        print( "TclVersion is", tk.TclVersion )
        print( "TkVersion is", tk.TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of Help.py