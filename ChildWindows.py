#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ChildWindows.py
#
# Base of Bible and lexicon resource windows for Biblelator Bible display/editing
#
# Copyright (C) 2013-2014 Robert Hunt
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
Base windows to allow display and manipulation of
    various Bible and lexicon, etc. child windows.
"""

from gettext import gettext as _

LastModifiedDate = '2014-12-08'
ShortProgName = "ChildWindows"
ProgName = "Biblelator Child Windows"
ProgVersion = '0.27'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import sys, os.path, logging, re

import tkinter as tk
from tkinter.simpledialog import askstring, askinteger
from tkinter.ttk import Style, Scrollbar, Label

# Biblelator imports
from BiblelatorGlobals import APP_NAME, START, DEFAULT, parseWindowSize, \
                             INITIAL_RESOURCE_SIZE, MINIMUM_RESOURCE_SIZE, MAXIMUM_RESOURCE_SIZE, \
                             INITIAL_HTML_SIZE, MINIMUM_HTML_SIZE, MAXIMUM_HTML_SIZE
from BiblelatorDialogs import errorBeep, showerror, showinfo
from TextBoxes import HTMLText

# BibleOrgSys imports
sourceFolder = "../BibleOrgSys/"
sys.path.append( sourceFolder )
import BibleOrgSysGlobals



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



class ChildBox():
    """
    A set of functions that work for any frame or window that has a member: self.textBox
    """
    def __init__( self, parentApp ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.__init__( {} )").format( parentApp ) )
            assert( parentApp )
        self.parentApp = parentApp

        self.myKeyboardBindingsList = []
        if BibleOrgSysGlobals.debugFlag: self.myKeyboardShortcutsList = []
    # end of ChildBox.__init__


    def createStandardKeyboardBinding( self, name, command ):
        """
        Called from createStandardKeyboardBindings to do the actual work.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildBox.createStandardKeyboardBinding( {} )").format( name ) )
        try: kBD = self.parentApp.keyBindingDict
        except AttributeError: kBD = self.parentWindow.parentApp.keyBindingDict
        assert( (name,kBD[name][0],) not in self.myKeyboardBindingsList )
        if name in kBD:
            for keyCode in kBD[name][1:]:
                #print( "Bind {} for {}".format( repr(keyCode), repr(name) ) )
                self.textBox.bind( keyCode, command )
                if BibleOrgSysGlobals.debugFlag:
                    assert( keyCode not in self.myKeyboardShortcutsList )
                    self.myKeyboardShortcutsList.append( keyCode )
            self.myKeyboardBindingsList.append( (name,kBD[name][0],) )
        else: logging.critical( 'No key binding available for {}'.format( repr(name) ) )
    # end of ChildBox.createStandardKeyboardBinding()

    def createStandardKeyboardBindings( self ):
        """
        Create keyboard bindings for this widget.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.createStandardKeyboardBindings()") )
        for name,command in ( ('SelectAll',self.doSelectAll), ('Copy',self.doCopy),
                             ('Find',self.doFind), ('Refind',self.doRefind),
                             ('Help',self.doHelp), ('Info',self.doShowInfo), ('About',self.doAbout),
                             ('Close',self.doClose) ):
            self.createStandardKeyboardBinding( name, command )
    # end of ChildBox.createStandardKeyboardBindings()


    def setFocus( self, event ):
        '''Explicitly set focus, so user can select and copy text'''
        self.textBox.focus_set()


    def doCopy( self, event=None ):
        """
        Copy the selected text onto the clipboard.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.doCopy()") )
        if not self.textBox.tag_ranges( tk.SEL ):       # save in cross-app clipboard
            errorBeep()
            showerror( self, APP_NAME, 'No text selected')
        else:
            copyText = self.textBox.get( tk.SEL_FIRST, tk.SEL_LAST)
            print( "  copied text", repr(copyText) )
            self.clipboard_clear()
            self.clipboard_append( copyText )
    # end of ChildBox.doCopy


    def doSelectAll( self, event=None ):
        """
        Select all the text in the text box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.doSelectAll()") )
        self.textBox.tag_add( tk.SEL, START, tk.END+'-1c' )   # select entire text
        self.textBox.mark_set( tk.INSERT, START )          # move insert point to top
        self.textBox.see( tk.INSERT )                      # scroll to top
    # end of ChildBox.doSelectAll


    def doGotoLine( self, event=None, forceline=None ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.doGotoLine()") )
        line = forceline or askinteger( APP_NAME, _("Enter line number") )
        self.textBox.update()
        self.textBox.focus()
        if line is not None:
            maxindex = self.textBox.index( tk.END+'-1c' )
            maxline  = int( maxindex.split('.')[0] )
            if line > 0 and line <= maxline:
                self.textBox.mark_set( tk.INSERT, '{}.0'.format(line) ) # goto line
                self.textBox.tag_remove( tk.SEL, START, tk.END )          # delete selects
                self.textBox.tag_add( tk.SEL, tk.INSERT, 'insert+1l' )  # select line
                self.textBox.see( tk.INSERT )                          # scroll to line
            else:
                errorBeep()
                showerror( self, APP_NAME, _("No such line number") )
    # end of ChildBox.doGotoLine


    def doFind( self, event=None, lastkey=None ):
        key = lastkey or askstring( APP_NAME, _("Enter search string") )
        self.textBox.update()
        self.textBox.focus()
        self.lastfind = key
        if key:
            nocase = self.optionsDict['caseinsens']
            where = self.textBox.search( key, tk.INSERT, tk.END, nocase=nocase )
            if not where:                                          # don't wrap
                errorBeep()
                showerror( self, APP_NAME, 'String not found' )
            else:
                pastkey = where + '+%dc' % len(key)           # index past key
                self.textBox.tag_remove( tk.SEL, START, tk.END )         # remove any sel
                self.textBox.tag_add( tk.SEL, where, pastkey )        # select key
                self.textBox.mark_set( tk.INSERT, pastkey )           # for next find
                self.textBox.see( where )                          # scroll display
    # end of ChildBox.doFind


    def doRefind( self, event=None ):
        self.doFind( self.lastfind)
    # end of ChildBox.doRefind


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog giving text statistics and cursor location;
        caveat (2.1): Tk insert position column counts a tab as one
        character: translate to next multiple of 8 to match visual?
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildBox.doShowInfo()") )
        text  = self.getAllText()
        numChars = len( text )
        numLines = len( text.split('\n') )
        numWords = len( text.split() )
        index = self.textBox.index( tk.INSERT )
        atLine, atColumn = index.split('.')
        showinfo( self, 'Window Information',
                 'Current location:\n' +
                 '  Line:\t{}\n  Column:\t{}\n'.format( atLine, atColumn ) +
                 '\nFile text statistics:\n' +
                 '  Chars:\t{}\n  Lines:\t{}\n  Words:\t{}\n'.format( numChars, numLines, numWords ) )
    # end of ChildBox.doShowInfo


    ############################################################################
    # Utilities, useful outside this class
    ############################################################################

    def clearText( self ): # Leaves in normal state
        self.textBox['state'] = tk.NORMAL
        self.textBox.delete( START, tk.END )
    # end of ChildBox.updateText


    def isEmpty( self ):
        return not self.getAllText()
    # end of ChildBox.isEmpty


    def modified( self ):
        return self.textBox.edit_modified()
    # end of ChildBox.modified


    def getAllText( self ):
        """ Returns all the text as a string. """
        return self.textBox.get( START, tk.END+'-1c' )
    # end of ChildBox.getAllText


    def setAllText( self, newText ):
        """
        Sets the textBox (assumed to be enabled) to the given text
            then positions the insert cursor at the BEGINNING of the text.

        caller: call self.update() first if just packed, else the
        initial position may be at line 2, not line 1 (2.1; Tk bug?)
        """
        self.textBox['state'] = tk.NORMAL
        self.textBox.delete( START, tk.END ) # Delete everything that's existing
        self.textBox.insert( tk.END, newText )
        self.textBox.mark_set( tk.INSERT, START ) # move insert point to top
        self.textBox.see( tk.INSERT ) # scroll to top, insert is set

        self.textBox.edit_reset() # clear undo/redo stks
        self.textBox.edit_modified( tk.FALSE ) # clear modified flag
    # end of ChildBox.setAllText


    def doClose( self, event=None ):
        """
        Called from the GUI.

        Can be overridden.
        """
        self.destroy()
    # end of ChildWindow.doClose
# end of ChildBox class



class ChildWindow( tk.Toplevel, ChildBox ):
    """
    """
    def __init__( self, parentApp, genericWindowType ):
        """
        The genericWindowType is set here,
            but the more specific winType is set later by the subclass.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("ChildWindow.__init__( {} {} )").format( parentApp, repr(genericWindowType) ) )
            assert( parentApp )
            assert( genericWindowType in ('BibleResource','LexiconResource','TextEditor','BibleEditor',) )
        self.parentApp, self.genericWindowType = parentApp, genericWindowType
        tk.Toplevel.__init__( self, self.parentApp )
        ChildBox.__init__( self, self.parentApp )
        self.protocol( "WM_DELETE_WINDOW", self.closeChildWindow )

        self.geometry( INITIAL_RESOURCE_SIZE )
        self.minimumSize, self.maximumSize = MINIMUM_RESOURCE_SIZE, MAXIMUM_RESOURCE_SIZE
        self.minsize( *parseWindowSize( self.minimumSize ) )
        self.maxsize( *parseWindowSize( self.maximumSize ) )

        self.createMenuBar()
        self.createToolBar()
        self.createContextMenu()

        self.viewMode = DEFAULT
        self.settings = None

        # Create a scroll bar to fill the right-hand side of the window
        self.vScrollbar = Scrollbar( self )
        self.vScrollbar.pack( side=tk.RIGHT, fill=tk.Y )

        #if 'textBox' in dir(self): # we have one already -- presumably a specialised one
            #halt # We have one already
        #else: # let's make one

        self.textBox = tk.Text( self, yscrollcommand=self.vScrollbar.set, state=tk.DISABLED )
        self.textBox['wrap'] = 'word'
        self.textBox.pack( expand=tk.YES, fill=tk.BOTH )
        self.vScrollbar.config( command=self.textBox.yview ) # link the scrollbar to the text box
        self.createStandardKeyboardBindings()
        self.textBox.bind( "<Button-1>", self.setFocus ) # So disabled text box can still do select and copy functions

        # Options for find, etc.
        self.optionsDict = {}
        self.optionsDict['caseinsens'] = True

        self.refreshTitle() # Must be in superclass
    # end of ChildWindow.__init__


    def notWrittenYet( self ):
        errorBeep()
        showerror( self, _("Not implemented"), _("Not yet available, sorry") )
    # end of ChildWindow.notWrittenYet


    def createMenuBar( self ):
        logging.critical( t("PROGRAMMING ERROR: This 'createMenuBar' method MUST be overridden!") )
        if BibleOrgSysGlobals.debugFlag:
            print( t("This 'createMenuBar' method MUST be overridden!") )
            halt


    def createContextMenu( self ):
        """
        Can be overriden if necessary.
        """
        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label="Copy", underline=0, command=self.doCopy, accelerator=self.parentApp.keyBindingDict['Copy'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Select all", underline=7, command=self.doSelectAll, accelerator=self.parentApp.keyBindingDict['SelectAll'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Find...", underline=0, command=self.doFind, accelerator=self.parentApp.keyBindingDict['Find'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Close", underline=1, command=self.doClose, accelerator=self.parentApp.keyBindingDict['Close'][0] )

        self.bind( "<Button-3>", self.showContextMenu ) # right-click
        #self.pack()
    # end of ChildWindow.createContextMenu


    def showContextMenu( self, event ):
        self.contextMenu.post( event.x_root, event.y_root )
    # end of ChildWindow.showContextMenu


    def createToolBar( self ):
        """
        Designed to be overridden.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( t("This 'createToolBar' method can be overridden!") )
        pass
    # end of ChildWindow.createToolBar


    def doHelp( self, event=None ):
        """
        Display a help box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindow.doHelp()") )
        from Help import HelpBox

        helpInfo = ProgNameVersion
        helpInfo += "\nHelp for {}".format( self.winType )
        helpInfo += "\n  Keyboard shortcuts:"
        for name,shortcut in self.myKeyboardBindingsList:
            helpInfo += "\n    {}\t{}".format( name, shortcut )
        hb = HelpBox( self, self.genericWindowType, helpInfo )
    # end of ChildWindow.doHelp


    def doAbout( self, event=None ):
        """
        Display an about box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindow.doAbout()") )
        from About import AboutBox

        aboutInfo = ProgNameVersion
        aboutInfo += "\nInformation about {}".format( self.winType )
        ab = AboutBox( self, self.genericWindowType, aboutInfo )
    # end of ChildWindow.doAbout


    def doClose( self, event=None ):
        """
        Called from the GUI.

        Can be overridden.
        """
        self.closeChildWindow()
    # end of ChildWindow.doClose

    def closeChildWindow( self ):
        """
        Called to finally and irreversibly remove this window from our list and close it.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindow.closeChildWindow()") )
        if self in self.parentApp.childWindows:
            self.parentApp.childWindows.remove( self )
            self.destroy()
        else: # we might not have finished making our window yet
            if BibleOrgSysGlobals.debugFlag:
                print( t("ChildWindow.closeChildWindow() for {} wasn't in list").format( self.winType ) )
            try: self.destroy()
            except tk.TclError: pass # never mind
        if BibleOrgSysGlobals.debugFlag: self.parentApp.setDebugText( "Closed resource window" )
    # end of ChildWindow.closeChildWindow
# end of class ChildWindow



class ChildWindows( list ):
    """
    Just keeps a list of the resource (Toplevel) windows.
    """
    def __init__( self, ChildWindowsParent ):
        self.ChildWindowsParent = ChildWindowsParent
        list.__init__( self )


    def iconify( self ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindows.iconify()") )
        for appWin in self:
            appWin.iconify()
    #end of ChildWindows.iconify


    def iconifyResources( self ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindows.iconifyResources()") )
        for appWin in self:
            if 'Resource' in appWin.genericWindowType:
                appWin.iconify()
    #end of ChildWindows.iconifyResources


    def deiconify( self ):
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("ChildWindows.deiconify()") )
        for appWin in self:
            appWin.deiconify()
            appWin.lift( aboveThis=self.ChildWindowsParent )
    #end of ChildWindows.deiconify


    def updateThisBibleGroup( self, groupCode, newVerseKey ):
        """
        Called when we probably need to update some resource windows with a new Bible reference.
        """
        if BibleOrgSysGlobals.debugFlag: print( t("ChildWindows.updateThisBibleGroup( {}, {} )").format( groupCode, newVerseKey ) )
        for appWin in self:
            if 'Bible' in appWin.genericWindowType: # e.g., BibleResource, BibleEditor
                if appWin.groupCode == groupCode:
                    # The following line doesn't work coz it only updates ONE window
                    #self.ChildWindowsParent.after_idle( lambda: appWin.updateShownBCV( newVerseKey ) )
                    appWin.updateShownBCV( newVerseKey )
    # end of ChildWindows.updateThisBibleGroup


    def updateLexicons( self, newLexiconWord ):
        """
        Called when we probably need to update some resource windows with a new word.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( t("ChildWindows.updateLexicons( {} )").format( newLexiconWord ) )
        for appWin in self:
            #print( "gwT", appWin.genericWindowType )
            if appWin.genericWindowType == 'LexiconResource':
                # The following line doesn't work coz it only updates ONE window
                #self.ChildWindowsParent.after_idle( lambda: appWin.updateLexiconWord( newLexiconWord ) )
                appWin.updateLexiconWord( newLexiconWord )
    # end of ChildWindows.updateLexicons
# end of ChildWindows class



class HTMLWindow( tk.Toplevel, ChildBox ):
    """
    """
    def __init__( self, parentWindow, filename=None ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("HTMLWindow.__init__( {}, {} )").format( parentWindow, repr(filename) ) )
            assert( parentWindow )
        self.parentWindow, self.initialFilename = parentWindow, filename
        tk.Toplevel.__init__( self, self.parentWindow )
        ChildBox.__init__( self, self.parentWindow )
        self.protocol( "WM_DELETE_WINDOW", self.closeHTMLWindow )
        self.title( 'HTMLWindow' )
        self.winType = 'HTMLWindow'

        self.geometry( INITIAL_HTML_SIZE )
        self.minimumSize, self.maximumSize = MINIMUM_HTML_SIZE, MAXIMUM_HTML_SIZE
        self.minsize( *parseWindowSize( self.minimumSize ) )
        self.maxsize( *parseWindowSize( self.maximumSize ) )

        self.showStatusBar = True

        self.createMenuBar()
        self.createToolBar()
        self.createContextMenu()
        self.createStatusBar()

        self.viewMode = DEFAULT
        self.settings = None

        # Create a scroll bar to fill the right-hand side of the window
        self.vScrollbar = Scrollbar( self )
        self.vScrollbar.pack( side=tk.RIGHT, fill=tk.Y )

        #if 'textBox' in dir(self): # we have one already -- presumably a specialised one
            #halt # We have one already
        #else: # let's make one

        self.textBox = HTMLText( self, yscrollcommand=self.vScrollbar.set, state=tk.DISABLED )
        self.textBox['wrap'] = 'word'
        self.textBox.pack( expand=tk.YES, fill=tk.BOTH )
        self.vScrollbar.config( command=self.textBox.yview ) # link the scrollbar to the text box
        self.createStandardKeyboardBindings()
        self.textBox.bind( "<Button-1>", self.setFocus ) # So disabled text box can still do select and copy functions

        # Options for find, etc.
        self.optionsDict = {}
        self.optionsDict['caseinsens'] = True

        if filename:
            self.historyList = [ filename ]
            self.historyIndex = 1 # Number from the end (starting with 1)
            self.load( filename )
        else:
            self.historyList = []
            self.historyIndex = 0 # = None
    # end of HTMLWindow.__init__


    def notWrittenYet( self ):
        errorBeep()
        showerror( self, _("Not implemented"), _("Not yet available, sorry") )
    # end of HTMLWindow.notWrittenYet


    def createMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.createMenuBar()") )
        try: kBD = self.parentWindow.parentApp.keyBindingDict
        except AttributeError: kBD = self.parentApp.keyBindingDict

        self.menubar = tk.Menu( self )
        #self['menu'] = self.menubar
        self.config( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label='File', underline=0 )
        #fileMenu.add_command( label='New...', underline=0, command=self.notWrittenYet )
        #fileMenu.add_command( label='Open...', underline=0, command=self.notWrittenYet )
        #fileMenu.add_separator()
        #subfileMenuImport = tk.Menu( fileMenu )
        #subfileMenuImport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Import', underline=0, menu=subfileMenuImport )
        #subfileMenuExport = tk.Menu( fileMenu )
        #subfileMenuExport.add_command( label='USX', underline=0, command=self.notWrittenYet )
        #subfileMenuExport.add_command( label='HTML', underline=0, command=self.notWrittenYet )
        #fileMenu.add_cascade( label='Export', underline=0, menu=subfileMenuExport )
        #fileMenu.add_separator()
        fileMenu.add_command( label='Info...', underline=0, command=self.doShowInfo, accelerator=kBD['Info'][0] )
        fileMenu.add_separator()
        fileMenu.add_command( label='Close', underline=0, command=self.doClose, accelerator=kBD['Close'][0] ) # close this window

        editMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=editMenu, label='Edit', underline=0 )
        editMenu.add_command( label='Copy', underline=0, command=self.doCopy, accelerator=kBD['Copy'][0] )
        editMenu.add_separator()
        editMenu.add_command( label='Select all', underline=0, command=self.doSelectAll, accelerator=kBD['SelectAll'][0] )

        searchMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=searchMenu, label='Search', underline=0 )
        searchMenu.add_command( label='Goto line...', underline=0, command=self.doGotoLine, accelerator=kBD['Line'][0] )
        searchMenu.add_separator()
        searchMenu.add_command( label='Find...', underline=0, command=self.doFind, accelerator=kBD['Find'][0] )
        searchMenu.add_command( label='Find again', underline=5, command=self.doRefind, accelerator=kBD['Refind'][0] )

        viewMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=viewMenu, label='View', underline=0 )
        viewMenu.add_command( label='Status bar', underline=0, command=self.notWrittenYet )

        gotoMenu = tk.Menu( self.menubar )
        self.menubar.add_cascade( menu=gotoMenu, label='Goto', underline=0 )
        gotoMenu.add_command( label='Back', underline=0, command=self.doGoBackward )
        gotoMenu.add_command( label='Forward', underline=0, command=self.doGoForward )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label='Tools', underline=0 )
        toolsMenu.add_command( label='Options...', underline=0, command=self.notWrittenYet )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label='Window', underline=0 )
        windowMenu.add_command( label='Bring in', underline=0, command=self.notWrittenYet )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, underline=0, label='Help' )
        helpMenu.add_command( label='Help...', underline=0, command=self.doHelp, accelerator=kBD['Help'][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label='About...', underline=0, command=self.doAbout, accelerator=kBD['About'][0] )
    # end of HTMLWindow.createMenuBar


    def createContextMenu( self ):
        """
        Can be overriden if necessary.
        """
        try: kBD = self.parentWindow.parentApp.keyBindingDict
        except AttributeError: kBD = self.parentApp.keyBindingDict

        self.contextMenu = tk.Menu( self, tearoff=0 )
        self.contextMenu.add_command( label="Copy", underline=0, command=self.doCopy, accelerator=kBD['Copy'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Select all", underline=7, command=self.doSelectAll, accelerator=kBD['SelectAll'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Find...", underline=0, command=self.doFind, accelerator=kBD['Find'][0] )
        self.contextMenu.add_separator()
        self.contextMenu.add_command( label="Close", underline=1, command=self.doClose, accelerator=kBD['Close'][0] )

        self.bind( "<Button-3>", self.showContextMenu ) # right-click
        #self.pack()
    # end of HTMLWindow.createContextMenu


    def showContextMenu( self, event ):
        self.contextMenu.post( event.x_root, event.y_root )
    # end of HTMLWindow.showContextMenu


    def createToolBar( self ):
        """
        Designed to be overridden.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( t("This 'createToolBar' method can be overridden!") )
        pass
    # end of HTMLWindow.createToolBar


    def createStatusBar( self ):
        """
        Create a status bar containing only one text label at the bottom of the main window.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("createStatusBar()") )
        Style().configure( 'StatusBar.TLabel', background='pink' )

        self.statusTextVariable = tk.StringVar()
        self.statusTextLabel = Label( self, relief=tk.SUNKEN,
                                    textvariable=self.statusTextVariable, style='StatusBar.TLabel' )
                                    #, font=('arial',16,tk.NORMAL) )
        self.statusTextLabel.pack( side=tk.BOTTOM, fill=tk.X )
        self.statusTextVariable.set( '' ) # first initial value
        self.setReadyStatus()
    # end of HTMLWindow.createStatusBar

    def setStatus( self, newStatusText=None ):
        """
        Set (or clear) the status bar text.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("setStatus( {} )").format( repr(newStatusText) ) )
        #print( "SB is", repr( self.statusTextVariable.get() ) )
        if newStatusText != self.statusTextVariable.get(): # it's changed
            #self.statusBarTextWidget['state'] = tk.NORMAL
            #self.statusBarTextWidget.delete( '1.0', tk.END )
            #if newStatusText:
                #self.statusBarTextWidget.insert( '1.0', newStatusText )
            #self.statusBarTextWidget['state'] = tk.DISABLED # Don't allow editing
            #self.statusText = newStatusText
            self.statusTextVariable.set( newStatusText )
            self.statusTextLabel.update()
    # end of HTMLWindow.setStatus

    #def setWaitStatus( self, newStatusText ):
        #"""
        #Set the status bar text and change the cursor to the wait/hourglass cursor.
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( t("setWaitStatus( {} )").format( repr(newStatusText) ) )
        ##self.rootWindow.config( cursor='watch' ) # 'wait' can only be used on Windows
        #self.setStatus( newStatusText )
        #self.update()
    ## end of HTMLWindow.setWaitStatus

    def setReadyStatus( self ):
        """
        Sets the status line to "Ready"
            and sets the cursor to the normal cursor.
        """
        self.setStatus( _("Ready") )
        #self.config( cursor='' )
    # end of HTMLWindow.setReadyStatus


    def load( self, filepath ):
        """
        Loads the given HTML file into the window
            and also finds and sets the window title
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.load( {} )").format( filepath ) )
        self.folderPath, self.filename = os.path.split( filepath )
        with open( filepath, 'rt' ) as HTMLFile:
            fileContents = HTMLFile.read()
        match = re.search( '<title>(.+?)</title>', fileContents )
        if match:
            #print( '0', repr(match.group(0)) ) # This includes the entire match, i.e., with the <title> tags, etc.
            #print( '1', repr(match.group(1)) ) # This is just the title
            title = match.group(1).replace( '\n', ' ' ).replace( '\r', ' ' ).replace( '  ', ' ' )
            #print( "title", repr(title) )
            self.title( title )
        else: self.title( 'HTMLWindow' )
        self.setAllText( fileContents )
    # end of HTMLWindow.load


    def gotoLink( self, link ):
        """
        Loads the given HTML file into the window
            and also finds and sets the window title
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.gotoLink( {} )").format( link ) )
        if not os.path.isabs( link ): # relative filepath
            link = os.path.join( self.folderPath, link )
        self.load( link )
        self.historyList.append( link )
        self.historyIndex = 1
    # end of HTMLWindow.gotoLink


    def doGoForward( self ):
        """
        """
        if self.historyIndex > 1:
            self.historyIndex -= 1
            self.load( self.historyList[ -self.historyIndex ] )
    # end of BibleResourceWindow.doGoForward


    def doGoBackward( self ):
        """
        """
        if self.historyIndex < len( self.historyList ):
            self.historyIndex += 1
            self.load( self.historyList[ -self.historyIndex ] )
    # end of BibleResourceWindow.doGoBackward


    def doHelp( self, event=None ):
        """
        Display a help box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.doHelp()") )
        from Help import HelpBox

        helpInfo = ProgNameVersion
        helpInfo += "\nHelp for {}".format( self.winType )
        helpInfo += "\n  Keyboard shortcuts:"
        for name,shortcut in self.myKeyboardBindingsList:
            helpInfo += "\n    {}\t{}".format( name, shortcut )
        hb = HelpBox( self, self.genericWindowType, helpInfo )
    # end of HTMLWindow.doHelp


    def doAbout( self, event=None ):
        """
        Display an about box.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.doAbout()") )
        from About import AboutBox

        aboutInfo = ProgNameVersion
        aboutInfo += "\nInformation about {}".format( self.winType )
        ab = AboutBox( self, self.genericWindowType, aboutInfo )
    # end of HTMLWindow.doAbout


    def doClose( self, event=None ):
        """
        Called from the GUI.

        Can be overridden.
        """
        self.closeHTMLWindow()
    # end of HTMLWindow.doClose

    def closeHTMLWindow( self ):
        """
        Called to finally and irreversibly remove this window from our list and close it.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("HTMLWindow.closeHTMLWindow()") )
        try: cWs = self.parentWindow.parentApp.childWindows
        except AttributeError: cWs = self.parentApp.childWindows
        if self in cWs:
            cWs.remove( self )
            self.destroy()
        else: # we might not have finished making our window yet
            if BibleOrgSysGlobals.debugFlag:
                print( t("HTMLWindow.closeHTMLWindow() for {} wasn't in list").format( self.winType ) )
            try: self.destroy()
            except tk.TclError: pass # never mind
        if BibleOrgSysGlobals.debugFlag: self.parentWindow.parentApp.setDebugText( "Closed HTML window" )
    # end of HTMLWindow.closeHTMLWindow
# end of class HTMLWindow



def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk

    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( t("Running demo...") )

    tkRootWindow = Tk()
    tkRootWindow.title( ProgNameVersion )
    #settings = ApplicationSettings( 'BiblelatorData/', 'BiblelatorSettings/', ProgName )
    #settings.load()

    #application = Application( parent=tkRootWindow, settings=settings )
    # Calls to the window manager class (wm in Tk)
    #application.master.title( ProgNameVersion )
    #application.master.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()
# end of ChildWindows.demo


if __name__ == '__main__':
    from BibleOrgSysGlobals import setup, addStandardOptionsAndProcess, closedown
    import multiprocessing

    # Configure basic set-up
    parser = setup( ProgName, ProgVersion )
    addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables


    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    closedown( ProgName, ProgVersion )
# end of ChildWindows.py