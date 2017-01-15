#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Biblelator.py
#
# Main program for Biblelator Bible display/editing
#
# Copyright (C) 2013-2017 Robert Hunt
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

Note that many times in this application, where the term 'Bible' is used
    it can refer to any versified resource, e.g., typically including commentaries.
"""

from gettext import gettext as _

LastModifiedDate = '2017-01-15' # by RJH
ShortProgName = "Biblelator"
ProgName = "Biblelator"
ProgVersion = '0.40'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import sys, os, logging
from datetime import datetime
import multiprocessing, subprocess

import tkinter as tk
from tkinter.filedialog import Open, Directory, askopenfilename #, SaveAs
from tkinter.ttk import Style, Frame, Button, Combobox, Label, Entry

# Biblelator imports
from BiblelatorGlobals import APP_NAME, DEFAULT, START, errorBeep, \
        DATA_FOLDER_NAME, LOGGING_SUBFOLDER_NAME, SETTINGS_SUBFOLDER_NAME, \
        INITIAL_MAIN_SIZE, INITIAL_MAIN_SIZE_DEBUG, MAX_RECENT_FILES, \
        BIBLE_GROUP_CODES, MAX_PSEUDOVERSES, \
        DEFAULT_KEY_BINDING_DICT, \
        findHomeFolderPath, findUsername, \
        parseWindowGeometry, assembleWindowGeometryFromList, centreWindow
from BiblelatorDialogs import showerror, showwarning, showinfo, \
        SelectResourceBoxDialog, \
        GetNewProjectNameDialog, CreateNewProjectFilesDialog, GetNewCollectionNameDialog, \
        BookNameDialog, NumberButtonDialog
from BiblelatorHelpers import mapReferencesVerseKey, createEmptyUSFMBooks, parseEnteredBookname
from Settings import ApplicationSettings, ProjectSettings
from BiblelatorSettingsFunctions import parseAndApplySettings, writeSettingsFile, \
        saveNewWindowSetup, deleteExistingWindowSetup, applyGivenWindowsSettings, viewSettings, \
        doSendUsageStatistics
from ChildWindows import ChildWindows
from BibleResourceWindows import SwordBibleResourceWindow, InternalBibleResourceWindow, DBPBibleResourceWindow
from BibleResourceCollection import BibleResourceCollectionWindow
from BibleReferenceCollection import BibleReferenceCollectionWindow
from LexiconResourceWindows import BibleLexiconResourceWindow
from TextEditWindow import TextEditWindow
from USFMEditWindow import USFMEditWindow
#from ESFMEditWindow import ESFMEditWindow
from BiblelatorSettingsEditor import openBiblelatorSettingsEditor
from BOSManager import openBOSManager
from SwordManager import openSwordManager

# BibleOrgSys imports
sys.path.append( '../BibleOrgSys/' )
#if debuggingThisModule: print( 'sys.path = ', sys.path )
import BibleOrgSysGlobals
from BibleOrganizationalSystems import BibleOrganizationalSystem
from BibleVersificationSystems import BibleVersificationSystems
from DigitalBiblePlatform import DBPBibles
from VerseReferences import SimpleVerseKey
from BibleStylesheets import BibleStylesheet
from SwordResources import SwordType, SwordInterface
from USFMBible import USFMBible
from PTX7Bible import PTX7Bible, loadPTX7ProjectData



LOCK_FILENAME = '{}.lock'.format( APP_NAME )
TEXT_FILETYPES = [('All files',  '*'), ('Text files', '.txt')]
BIBLELATOR_PROJECT_FILETYPES = [('ProjectSettings','ProjectSettings.ini'), ('INI files','.ini'), ('All files','*')]
PARATEXT_FILETYPES = [('SSF files','.ssf'), ('All files','*')]



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



class Application( Frame ):
    """
    This is the main application window (well, actually a frame in the root toplevel window).

    Its main job is to keep track of self.currentVerseKey (and self.currentVerseKeyGroup)
        and use that to inform child windows of BCV movements.
    """
    global settings
    def __init__( self, rootWindow, homeFolderPath, loggingFolderPath, iconImage ):
        """
        Main app initialisation function.

        Creates the main menu and toolbar which includes the main BCV (book/chapter/verse) selector.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.__init__( {}, {}, {}, … )").format( rootWindow, homeFolderPath, loggingFolderPath ) )
        self.rootWindow, self.homeFolderPath, self.loggingFolderPath, self.iconImage = rootWindow, homeFolderPath, loggingFolderPath, iconImage
        self.parentApp = self # Yes, that's me, myself!
        self.starting = True

        if 0:
            from tkinter import font
            print( "tkDefaultFont", font.nametofont("TkDefaultFont").configure() )
            print( "tkTextFont", font.nametofont("TkTextFont").configure() )
            print( "tkFixedFont", font.nametofont("TkFixedFont").configure() )

        self.themeName = 'default'
        self.style = Style()
        self.interfaceLanguage = DEFAULT
        self.interfaceComplexity = DEFAULT
        self.touchMode = False # True makes larger buttons
        self.tabletMode = False
        self.showDebugMenu = False

        self.lastFind = None
        #self.openDialog = None
        self.saveDialog = None
        self.optionsDict = {}

        self.lexiconWord = None
        self.currentProject = None

        self.usageFilename = APP_NAME + 'UsageLog.txt'
        self.usageLogPath = os.path.join ( loggingFolderPath, self.usageFilename )
        self.lastLoggedUsageDate = self.lastLoggedUsageTime = None

        if BibleOrgSysGlobals.debugFlag: print( "Button default font", Style().lookup('TButton', 'font') )
        if BibleOrgSysGlobals.debugFlag: print( "Label default font", Style().lookup('TLabel', 'font') )

        # We rely on the parseAndApplySettings() call below to do this
        ## Set-up our Bible system and our callables
        #self.genericBibleOrganisationalSystemName = 'GENERIC-KJV-ENG' # Handles all bookcodes
        #self.setGenericBibleOrganisationalSystem( self.genericBibleOrganisationalSystemName )

        self.stylesheet = BibleStylesheet().loadDefault()
        Frame.__init__( self, self.rootWindow )
        self.pack()

        self.rootWindow.protocol( 'WM_DELETE_WINDOW', self.doCloseMe ) # Catch when app is closed

        self.childWindows = ChildWindows( self )

        self.createStatusBar()
        if BibleOrgSysGlobals.debugFlag: # Create a scrolling debug box
            self.lastDebugMessage = None
            from tkinter.scrolledtext import ScrolledText
            #Style().configure('DebugText.TScrolledText', padding=2, background='orange')
            self.debugTextBox = ScrolledText( self.rootWindow, bg='orange' )#style='DebugText.TScrolledText' )
            self.debugTextBox.pack( side=tk.BOTTOM, fill=tk.BOTH )
            #self.debugTextBox.tag_configure( 'emp', background='yellow', font='helvetica 12 bold', relief='tk.RAISED' )
            self.debugTextBox.tag_configure( 'emp', font='helvetica 10 bold' )
            self.setDebugText( "Starting up…" )

        self.SwordInterface = None
        self.DBPInterface = None
        #print( exp("Preload the Sword library…") )
        #self.SwordInterface = SwordResources.SwordInterface() # Preload the Sword library

        self.currentProjectName = 'TranslationTest'

        self.currentUserName = findUsername().title()
        self.currentUserInitials = self.currentUserName[0] # Default to first letter
        self.currentUserEmail = 'Unknown'
        self.currentUserRole = 'Translator'
        self.currentUserAssignments = 'ALL'

        # Set default folders
        self.lastFileDir = '.'
        self.lastBiblelatorFileDir = os.path.join( self.homeFolderPath, DATA_FOLDER_NAME )
        trySwordFolder = os.path.join( self.homeFolderPath, '.sword/' )
        if not os.path.isdir( trySwordFolder ): trySwordFolder = self.homeFolderPath
        self.lastSwordDir = trySwordFolder
        self.lastParatextFileDir = './'
        self.lastInternalBibleDir = './'
        if sys.platform.startswith( 'win' ):
            PT8Folder = 'C:\\My Paratext 8 Projects\\'
            PT7Folder = 'C:\\My Paratext Projects\\'
            self.lastParatextFileDir = PT8Folder if os.path.isdir( PT8Folder ) else PT7Folder
            self.lastInternalBibleDir = self.lastParatextFileDir
        elif sys.platform == 'linux': # temp hack XXXXXXXXXXXXX …
            #self.lastParatextFileDir = '../../../../../Data/Work/VirtualBox_Shared_Folder/'
            self.lastParatextFileDir = '../../../../../Data/Work/Matigsalug/Bible/'
            self.lastInternalBibleDir = '../../../../../Data/Work/Matigsalug/Bible/'

        self.keyBindingDict = DEFAULT_KEY_BINDING_DICT
        self.myKeyboardBindingsList = []
        self.recentFiles = []
        self.internalBibles = []

        #logging.critical( "Critical test" )
        #logging.error( "Error test" )
        #logging.warning( "Warning test" )
        #logging.info( "Info test" )
        #logging.debug( "Debug test" )
        #halt

        # Read and apply the saved settings
        self.viewVersesBefore, self.viewVersesAfter = 2, 6 # TODO: Not really the right place to have this
        if BibleOrgSysGlobals.commandLineArguments.override is None:
            self.INIname = APP_NAME
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "Using default {!r} ini file".format( self.INIname ) )
        else:
            self.INIname = BibleOrgSysGlobals.commandLineArguments.override
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Using settings from user-specified {!r} ini file").format( self.INIname ) )
        self.settings = ApplicationSettings( self.homeFolderPath, DATA_FOLDER_NAME, SETTINGS_SUBFOLDER_NAME, self.INIname )
        self.settings.load()
        parseAndApplySettings( self )
        if ProgName not in self.settings.data or 'windowSize' not in self.settings.data[ProgName] or 'windowPosition' not in self.settings.data[ProgName]:
            initialMainSize = INITIAL_MAIN_SIZE_DEBUG if BibleOrgSysGlobals.debugFlag else INITIAL_MAIN_SIZE
            centreWindow( self.rootWindow, *initialMainSize.split( 'x', 1 ) )

        if self.touchMode:
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Touch mode enabled!") )
            self.createTouchMenuBar()
            self.createTouchNavigationBar()
        else: # assume it's regular desktop mode
            self.createNormalMenuBar()
            self.createNormalNavigationBar()
        self.createToolBar()
        if BibleOrgSysGlobals.debugFlag: self.createDebugToolBar()
        self.createMainKeyboardBindings()

        self.BCVHistory = []
        self.BCVHistoryIndex = None

        # Make sure all our Bible windows get updated initially
        for groupCode in BIBLE_GROUP_CODES:
            if groupCode != self.currentVerseKeyGroup: # that gets done below
                groupVerseKey = self.getVerseKey( groupCode )
                if BibleOrgSysGlobals.debugFlag: assert isinstance( groupVerseKey, SimpleVerseKey )
                for appWin in self.childWindows:
                    if 'Bible' in appWin.genericWindowType:
                        if appWin._groupCode == groupCode:
                            appWin.updateShownBCV( groupVerseKey )
        self.updateBCVGroup( self.currentVerseKeyGroup ) # Does an acceptNewBnCV

        # See if there's any developer messages
        if self.internetAccessEnabled and self.checkForDeveloperMessagesEnabled:
            self.doCheckForMessagesFromDeveloper()

        self.setMainWindowTitle()
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "__init__ finished." )
        self.starting = False
        self.setReadyStatus()
        self.logUsage( ProgName, debuggingThisModule, 'Finished init Application {!r}, {!r}, …'.format( homeFolderPath, loggingFolderPath ) )
    # end of Application.__init__


    def setMainWindowTitle( self ):
        self.rootWindow.title( '[{}] {}'.format( self.currentVerseKeyGroup, ProgNameVersion ) \
                            + (' ({})'.format( self.currentUserName ) if self.currentUserName else '' ) )
    # end of Application.setMainWindowTitle


    def setGenericBibleOrganisationalSystem( self, BOSname ):
        """
        We usually use a fairly generic BibleOrganizationalSystem (BOS) to ensure
            that it contains all the books that we might ever want to navigate to.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setGenericBibleOrganisationalSystem( {} )").format( BOSname ) )

        # Set-up our Bible system and our callables
        self.genericBibleOrganisationalSystem = BibleOrganizationalSystem( self.genericBibleOrganisationalSystemName )
        self.genericBookList = self.genericBibleOrganisationalSystem.getBookList()
        #self.getNumBooks = self.genericBibleOrganisationalSystem.getNumBooks
        self.getNumChapters = self.genericBibleOrganisationalSystem.getNumChapters
        self.getNumVerses = lambda b,c: MAX_PSEUDOVERSES if c=='0' or c==0 \
                                        else self.genericBibleOrganisationalSystem.getNumVerses( b, c )
        self.isValidBCVRef = self.genericBibleOrganisationalSystem.isValidBCVRef
        self.getFirstBookCode = self.genericBibleOrganisationalSystem.getFirstBookCode
        self.getPreviousBookCode = self.genericBibleOrganisationalSystem.getPreviousBookCode
        self.getNextBookCode = self.genericBibleOrganisationalSystem.getNextBookCode
        self.getBBBFromText = self.genericBibleOrganisationalSystem.getBBBFromText
        self.getGenericBookName = self.genericBibleOrganisationalSystem.getBookName
        #self.getBookList = self.genericBibleOrganisationalSystem.getBookList

        # Make a bookNumber table with GEN as #1
        #print( self.genericBookList )
        self.offsetGenesis = self.genericBookList.index( 'GEN' )
        #print( 'offsetGenesis', self.offsetGenesis )
        self.bookNumberTable = {}
        for j,BBB in enumerate(self.genericBookList):
            k = j + 1 - self.offsetGenesis
            nBBB = BibleOrgSysGlobals.BibleBooksCodes.getReferenceNumber( BBB )
            #print( BBB, nBBB )
            self.bookNumberTable[k] = BBB
            self.bookNumberTable[BBB] = k
        #print( self.bookNumberTable )
    # end of Application.setGenericBibleOrganisationalSystem


    def createMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createMenuBar()") )

        if self.touchMode:
            self.createTouchMenuBar()
        else: # assume it's regular desktop mode
            self.createNormalMenuBar()
    # end of Application.createMenuBar

    def createNormalMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createNormalMenuBar()") )

        #self.win = Toplevel( self )
        self.menubar = tk.Menu( self.rootWindow )
        #self.rootWindow['menu'] = self.menubar
        self.rootWindow.configure( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        #fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        fileNewSubmenu = tk.Menu( fileMenu, tearoff=False )
        fileMenu.add_cascade( label=_('New'), underline=0, menu=fileNewSubmenu )
        fileNewSubmenu.add_command( label=_('Text file'), underline=0, command=self.doOpenNewTextEditWindow )
        fileOpenSubmenu = tk.Menu( fileMenu, tearoff=False )
        fileMenu.add_cascade( label=_('Open'), underline=0, menu=fileOpenSubmenu )
        fileRecentOpenSubmenu = tk.Menu( fileOpenSubmenu, tearoff=False )
        fileOpenSubmenu.add_cascade( label=_('Recent'), underline=0, menu=fileRecentOpenSubmenu )
        for j, (filename, folder, windowType) in enumerate( self.recentFiles ):
            fileRecentOpenSubmenu.add_command( label=filename, underline=0, command=lambda which=j: self.doOpenRecent(which) )
        fileOpenSubmenu.add_separator()
        fileOpenSubmenu.add_command( label=_('Text file…'), underline=0, command=self.doOpenFileTextEditWindow )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Save all…'), underline=0, command=self.doSaveAll )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Save settings'), underline=0, command=lambda: writeSettingsFile(self) )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Quit app'), underline=0, command=self.doCloseMe, accelerator=self.keyBindingDict[_('Quit')][0] ) # quit app

        #editMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        #editMenu.add_command( label=_('Find…'), underline=0, command=self.notWrittenYet )
        #editMenu.add_command( label=_('Replace…'), underline=0, command=self.notWrittenYet )

        gotoMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.notWrittenYet )
        gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.notWrittenYet )
        gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo )

        projectMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=projectMenu, label=_('Project'), underline=0 )
        projectMenu.add_command( label=_('New…'), underline=0, command=self.doStartNewProject )
        #submenuNewType = tk.Menu( resourcesMenu, tearoff=False )
        #projectMenu.add_cascade( label=_('New…'), underline=5, menu=submenuNewType )
        #submenuNewType.add_command( label=_('Text file…'), underline=0, command=self.doOpenNewTextEditWindow )
        #projectMenu.add_command( label=_('Open'), underline=0, command=self.notWrittenYet )
        submenuProjectOpenType = tk.Menu( projectMenu, tearoff=False )
        projectMenu.add_cascade( label=_('Open'), underline=0, menu=submenuProjectOpenType )
        submenuProjectOpenType.add_command( label=_('Biblelator…'), underline=0, command=self.doOpenBiblelatorProject )
        #submenuProjectOpenType.add_command( label=_('Bibledit…'), underline=0, command=self.doOpenBibleditProject )
        submenuProjectOpenType.add_command( label=_('Paratext…'), underline=0, command=self.doOpenParatextProject )
        projectMenu.add_separator()
        projectMenu.add_command( label=_('Backup…'), underline=0, command=self.notWrittenYet )
        projectMenu.add_command( label=_('Restore…'), underline=0, command=self.notWrittenYet )
        #projectMenu.add_separator()
        #projectMenu.add_command( label=_('Export'), underline=1, command=self.doProjectExports )
        projectMenu.add_separator()
        projectMenu.add_command( label=_('Hide all projects'), underline=0, command=self.doHideAllProjects )
        projectMenu.add_command( label=_('Show all projects'), underline=0, command=self.doShowAllProjects )

        resourcesMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=resourcesMenu, label=_('Resources'), underline=0 )
        submenuBibleResourceType = tk.Menu( resourcesMenu, tearoff=False )
        resourcesMenu.add_cascade( label=_('Open Bible/commentary'), underline=5, menu=submenuBibleResourceType )
        submenuBibleResourceType.add_command( label=_('Online (DBP)…'), underline=0, state=tk.NORMAL if self.internetAccessEnabled else tk.DISABLED, command=self.doOpenDBPBibleResourceWindow )
        submenuBibleResourceType.add_command( label=_('Sword module…'), underline=0, command=self.doOpenSwordResourceWindow )
        submenuBibleResourceType.add_command( label=_('Other (local)…'), underline=1, command=self.doOpenInternalBibleResourceWindow )
        submenuLexiconResourceType = tk.Menu( resourcesMenu, tearoff=False )
        resourcesMenu.add_cascade( label=_('Open lexicon'), menu=submenuLexiconResourceType )
        #submenuLexiconResourceType.add_command( label=_('Hebrew…'), underline=5, command=self.notWrittenYet )
        #submenuLexiconResourceType.add_command( label=_('Greek…'), underline=0, command=self.notWrittenYet )
        submenuLexiconResourceType.add_command( label=_('Bible'), underline=0, command=self.doOpenBibleLexiconResourceWindow )
        #submenuCommentaryResourceType = tk.Menu( resourcesMenu, tearoff=False )
        #resourcesMenu.add_cascade( label=_('Open commentary'), underline=5, menu=submenuCommentaryResourceType )
        resourcesMenu.add_command( label=_('Open resource collection…'), underline=5, command=self.doOpenNewBibleResourceCollectionWindow )
        resourcesMenu.add_separator()
        resourcesMenu.add_command( label=_('Hide all resources'), underline=0, command=self.doHideAllResources )
        resourcesMenu.add_command( label=_('Show all resources'), underline=0, command=self.doShowAllResources )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        toolsMenu.add_command( label=_('Search files…'), underline=0, command=self.onGrep )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('Checks…'), underline=0, command=self.notWrittenYet )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('Options…'), underline=0, command=self.doOpenSettingsEditor )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('BOS manager…'), underline=0, command=self.doOpenBOSManager )
        toolsMenu.add_command( label=_('Sword manager…'), underline=1, command=self.doOpenSwordManager )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        windowMenu.add_command( label=_('Hide resources'), underline=0, command=self.doHideAllResources )
        windowMenu.add_command( label=_('Hide projects'), underline=5, command=self.doHideAllProjects )
        windowMenu.add_command( label=_('Hide all'), underline=1, command=self.doHideAll )
        windowMenu.add_command( label=_('Show all'), underline=0, command=self.doShowAll )
        windowMenu.add_command( label=_('Bring all here'), underline=0, command=self.doBringAll )
        windowMenu.add_separator()
        windowMenu.add_command( label=_('Save window setup'), underline=0, command=lambda: saveNewWindowSetup(self) )
        if len(self.windowsSettingsDict)>1 or (self.windowsSettingsDict and 'Current' not in self.windowsSettingsDict):
            #windowMenu.add_command( label=_('Delete a window setting'), underline=0, command=self.doDeleteExistingWindowSetup )
            windowMenu.add_command( label=_('Delete a window setting'), underline=0, command=lambda: deleteExistingWindowSetup(self) )
            windowMenu.add_separator()
            for savedName in self.windowsSettingsDict:
                if savedName != 'Current':
                    windowMenu.add_command( label=savedName, command=lambda sN=savedName: applyGivenWindowsSettings(self,sN) )
        windowMenu.add_separator()
        submenuWindowStyle = tk.Menu( windowMenu, tearoff=False )
        windowMenu.add_cascade( label=_('Theme'), underline=0, menu=submenuWindowStyle )
        for themeName in self.style.theme_names():
            submenuWindowStyle.add_command( label=themeName.title(), underline=0, command=lambda tN=themeName: self.doChangeTheme(tN) )

        if self.showDebugMenu or BibleOrgSysGlobals.debugFlag:
            debugMenu = tk.Menu( self.menubar, tearoff=False )
            self.menubar.add_cascade( menu=debugMenu, label=_('Debug'), underline=0 )
            debugMenu.add_command( label=_('View open windows…'), underline=10, command=self.doViewWindowsList )
            debugMenu.add_command( label=_('View open Bibles…'), underline=10, command=self.doViewBiblesList )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('View settings…'), underline=0, command=self.doViewSettings )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('View log…'), underline=5, command=self.doViewLog )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('Submit bug…'), underline=0, command=self.doSubmitBug )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, label=_('Help'), underline=0 )
        helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.keyBindingDict[_('Help')][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('Submit bug…'), underline=0, state=tk.NORMAL if self.internetAccessEnabled else tk.DISABLED, command=self.doSubmitBug )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.keyBindingDict[_('About')][0] )
    # end of Application.createNormalMenuBar

    def createTouchMenuBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createTouchMenuBar()") )
            assert self.touchMode

        #self.win = Toplevel( self )
        self.menubar = tk.Menu( self.rootWindow )
        #self.rootWindow['menu'] = self.menubar
        self.rootWindow.configure( menu=self.menubar ) # alternative

        fileMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=fileMenu, label=_('File'), underline=0 )
        #fileMenu.add_command( label=_('New…'), underline=0, command=self.notWrittenYet )
        fileNewSubmenu = tk.Menu( fileMenu, tearoff=False )
        fileMenu.add_cascade( label=_('New'), underline=0, menu=fileNewSubmenu )
        fileNewSubmenu.add_command( label=_('Text file'), underline=0, command=self.doOpenNewTextEditWindow )
        fileOpenSubmenu = tk.Menu( fileMenu, tearoff=False )
        fileMenu.add_cascade( label=_('Open'), underline=0, menu=fileOpenSubmenu )
        fileRecentOpenSubmenu = tk.Menu( fileOpenSubmenu, tearoff=False )
        fileOpenSubmenu.add_cascade( label=_('Recent'), underline=0, menu=fileRecentOpenSubmenu )
        for j, (filename, folder, windowType) in enumerate( self.recentFiles ):
            fileRecentOpenSubmenu.add_command( label=filename, underline=0, command=lambda which=j: self.doOpenRecent(which) )
        fileOpenSubmenu.add_separator()
        fileOpenSubmenu.add_command( label=_('Text file…'), underline=0, command=self.doOpenFileTextEditWindow )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Save all…'), underline=0, command=self.doSaveAll )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Save settings'), underline=0, command=lambda: writeSettingsFile(self) )
        fileMenu.add_separator()
        fileMenu.add_command( label=_('Quit app'), underline=0, command=self.doCloseMe, accelerator=self.keyBindingDict[_('Quit')][0] ) # quit app

        #editMenu = tk.Menu( self.menubar, tearoff=False )
        #self.menubar.add_cascade( menu=editMenu, label=_('Edit'), underline=0 )
        #editMenu.add_command( label=_('Find…'), underline=0, command=self.notWrittenYet )
        #editMenu.add_command( label=_('Replace…'), underline=0, command=self.notWrittenYet )

        gotoMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=gotoMenu, label=_('Goto'), underline=0 )
        gotoMenu.add_command( label=_('Previous book'), underline=-1, command=self.doGotoPreviousBook )
        gotoMenu.add_command( label=_('Next book'), underline=-1, command=self.doGotoNextBook )
        gotoMenu.add_command( label=_('Previous chapter'), underline=-1, command=self.doGotoPreviousChapter )
        gotoMenu.add_command( label=_('Next chapter'), underline=-1, command=self.doGotoNextChapter )
        gotoMenu.add_command( label=_('Previous section'), underline=-1, command=self.notWrittenYet )
        gotoMenu.add_command( label=_('Next section'), underline=-1, command=self.notWrittenYet )
        gotoMenu.add_command( label=_('Previous verse'), underline=-1, command=self.doGotoPreviousVerse )
        gotoMenu.add_command( label=_('Next verse'), underline=-1, command=self.doGotoNextVerse )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Forward'), underline=0, command=self.doGoForward )
        gotoMenu.add_command( label=_('Backward'), underline=0, command=self.doGoBackward )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Previous list item'), underline=0, state=tk.DISABLED, command=self.doGotoPreviousListItem )
        gotoMenu.add_command( label=_('Next list item'), underline=0, state=tk.DISABLED, command=self.doGotoNextListItem )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Book'), underline=0, command=self.doGotoBook )
        gotoMenu.add_separator()
        gotoMenu.add_command( label=_('Info…'), underline=0, command=self.doShowInfo )

        projectMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=projectMenu, label=_('Project'), underline=0 )
        projectMenu.add_command( label=_('New…'), underline=0, command=self.doStartNewProject )
        #submenuNewType = tk.Menu( resourcesMenu, tearoff=False )
        #projectMenu.add_cascade( label=_('New…'), underline=5, menu=submenuNewType )
        #submenuNewType.add_command( label=_('Text file…'), underline=0, command=self.doOpenNewTextEditWindow )
        #projectMenu.add_command( label=_('Open'), underline=0, command=self.notWrittenYet )
        submenuProjectOpenType = tk.Menu( projectMenu, tearoff=False )
        projectMenu.add_cascade( label=_('Open'), underline=0, menu=submenuProjectOpenType )
        submenuProjectOpenType.add_command( label=_('Biblelator…'), underline=0, command=self.doOpenBiblelatorProject )
        #submenuProjectOpenType.add_command( label=_('Bibledit…'), underline=0, command=self.doOpenBibleditProject )
        submenuProjectOpenType.add_command( label=_('Paratext…'), underline=0, command=self.doOpenParatextProject )
        projectMenu.add_separator()
        projectMenu.add_command( label=_('Backup…'), underline=0, command=self.notWrittenYet )
        projectMenu.add_command( label=_('Restore…'), underline=0, command=self.notWrittenYet )
        #projectMenu.add_separator()
        #projectMenu.add_command( label=_('Export'), underline=1, command=self.doProjectExports )
        projectMenu.add_separator()
        projectMenu.add_command( label=_('Hide all projects'), underline=0, command=self.doHideAllProjects )
        projectMenu.add_command( label=_('Show all projects'), underline=0, command=self.doShowAllProjects )

        resourcesMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=resourcesMenu, label=_('Resources'), underline=0 )
        submenuBibleResourceType = tk.Menu( resourcesMenu, tearoff=False )
        resourcesMenu.add_cascade( label=_('Open Bible/commentary'), underline=5, menu=submenuBibleResourceType )
        submenuBibleResourceType.add_command( label=_('Online (DBP)…'), underline=0, state=tk.NORMAL if self.internetAccessEnabled else tk.DISABLED, command=self.doOpenDBPBibleResourceWindow )
        submenuBibleResourceType.add_command( label=_('Sword module…'), underline=0, command=self.doOpenSwordResourceWindow )
        submenuBibleResourceType.add_command( label=_('Other (local)…'), underline=1, command=self.doOpenInternalBibleResourceWindow )
        submenuLexiconResourceType = tk.Menu( resourcesMenu, tearoff=False )
        resourcesMenu.add_cascade( label=_('Open lexicon'), menu=submenuLexiconResourceType )
        #submenuLexiconResourceType.add_command( label=_('Hebrew…'), underline=5, command=self.notWrittenYet )
        #submenuLexiconResourceType.add_command( label=_('Greek…'), underline=0, command=self.notWrittenYet )
        submenuLexiconResourceType.add_command( label=_('Bible'), underline=0, command=self.doOpenBibleLexiconResourceWindow )
        #submenuCommentaryResourceType = tk.Menu( resourcesMenu, tearoff=False )
        #resourcesMenu.add_cascade( label=_('Open commentary'), underline=5, menu=submenuCommentaryResourceType )
        resourcesMenu.add_command( label=_('Open resource collection…'), underline=5, command=self.doOpenNewBibleResourceCollectionWindow )
        resourcesMenu.add_separator()
        resourcesMenu.add_command( label=_('Hide all resources'), underline=0, command=self.doHideAllResources )
        resourcesMenu.add_command( label=_('Show all resources'), underline=0, command=self.doShowAllResources )

        toolsMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=toolsMenu, label=_('Tools'), underline=0 )
        toolsMenu.add_command( label=_('Search files…'), underline=0, command=self.onGrep )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('Checks…'), underline=0, command=self.notWrittenYet )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('Options…'), underline=0, command=self.doOpenSettingsEditor )
        toolsMenu.add_separator()
        toolsMenu.add_command( label=_('BOS manager…'), underline=0, command=self.doOpenBOSManager )
        toolsMenu.add_command( label=_('Sword manager…'), underline=1, command=self.doOpenSwordManager )

        windowMenu = tk.Menu( self.menubar, tearoff=False )
        self.menubar.add_cascade( menu=windowMenu, label=_('Window'), underline=0 )
        windowMenu.add_command( label=_('Hide resources'), underline=5, command=self.doHideAllResources )
        windowMenu.add_command( label=_('Hide projects'), underline=5, command=self.doHideAllProjects )
        windowMenu.add_command( label=_('Hide all'), underline=0, command=self.doHideAll )
        windowMenu.add_command( label=_('Show all'), underline=0, command=self.doShowAll )
        windowMenu.add_command( label=_('Bring all here'), underline=0, command=self.doBringAll )
        windowMenu.add_separator()
        windowMenu.add_command( label=_('Save window setup'), underline=0, command=lambda: saveNewWindowSetup(self) )
        if len(self.windowsSettingsDict)>1 or (self.windowsSettingsDict and 'Current' not in self.windowsSettingsDict):
            #windowMenu.add_command( label=_('Delete a window setting'), underline=0, command=self.doDeleteExistingWindowSetup )
            windowMenu.add_command( label=_('Delete a window setting'), underline=0, command=lambda: deleteExistingWindowSetup(self) )
            windowMenu.add_separator()
            for savedName in self.windowsSettingsDict:
                if savedName != 'Current':
                    windowMenu.add_command( label=savedName, underline=0, command=lambda sN=savedName: applyGivenWindowsSettings(self,sN) )
        windowMenu.add_separator()
        submenuWindowStyle = tk.Menu( windowMenu, tearoff=False )
        windowMenu.add_cascade( label=_('Theme'), underline=0, menu=submenuWindowStyle )
        for themeName in self.style.theme_names():
            submenuWindowStyle.add_command( label=themeName.title(), underline=0, command=lambda tN=themeName: self.doChangeTheme(tN) )

        if self.showDebugMenu or BibleOrgSysGlobals.debugFlag:
            debugMenu = tk.Menu( self.menubar, tearoff=False )
            self.menubar.add_cascade( menu=debugMenu, label=_('Debug'), underline=0 )
            debugMenu.add_command( label=_('View open windows…'), underline=10, command=self.doViewWindowsList )
            debugMenu.add_command( label=_('View open Bibles…'), underline=10, command=self.doViewBiblesList )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('View settings…'), underline=0, command=self.doViewSettings )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('View log…'), underline=5, command=self.doViewLog )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('Submit bug…'), underline=0, command=self.doSubmitBug )
            debugMenu.add_separator()
            debugMenu.add_command( label=_('Options…'), underline=0, command=self.notWrittenYet )

        helpMenu = tk.Menu( self.menubar, name='help', tearoff=False )
        self.menubar.add_cascade( menu=helpMenu, label=_('Help'), underline=0 )
        helpMenu.add_command( label=_('Help…'), underline=0, command=self.doHelp, accelerator=self.keyBindingDict[_('Help')][0] )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('Submit bug…'), underline=0, state=tk.NORMAL if self.internetAccessEnabled else tk.DISABLED, command=self.doSubmitBug )
        helpMenu.add_separator()
        helpMenu.add_command( label=_('About…'), underline=0, command=self.doAbout, accelerator=self.keyBindingDict[_('About')][0] )
    # end of Application.createTouchMenuBar


    def createNormalNavigationBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createNormalNavigationBar()") )

        Style().configure('NavigationBar.TFrame', background='yellow')

        navigationBar = Frame( self, cursor='hand2', relief=tk.RAISED, style='NavigationBar.TFrame' )

        self.previousBCVButton = Button( navigationBar, width=4, text='<-', command=self.doGoBackward, state=tk.DISABLED )
        self.previousBCVButton.pack( side=tk.LEFT )
        self.nextBCVButton = Button( navigationBar, width=4, text='->', command=self.doGoForward, state=tk.DISABLED )
        self.nextBCVButton.pack( side=tk.LEFT )

        Style().configure( 'A.TButton', background='lightgreen' )
        Style().configure( 'B.TButton', background='pink' )
        Style().configure( 'C.TButton', background='orange' )
        Style().configure( 'D.TButton', background='brown' )
        Style().configure( 'E.TButton', background='aqua' )
        self.GroupAButton = Button( navigationBar, width=2, text='A', style='A.TButton', command=self.selectGroupA, state=tk.DISABLED )
        self.GroupBButton = Button( navigationBar, width=2, text='B', style='B.TButton', command=self.selectGroupB, state=tk.DISABLED )
        self.GroupCButton = Button( navigationBar, width=2, text='C', style='C.TButton', command=self.selectGroupC, state=tk.DISABLED )
        self.GroupDButton = Button( navigationBar, width=2, text='D', style='D.TButton', command=self.selectGroupD, state=tk.DISABLED )
        self.GroupEButton = Button( navigationBar, width=2, text='E', style='E.TButton', command=self.selectGroupE, state=tk.DISABLED )
        self.GroupAButton.pack( side=tk.LEFT )
        self.GroupBButton.pack( side=tk.LEFT )
        self.GroupCButton.pack( side=tk.LEFT )
        self.GroupDButton.pack( side=tk.LEFT )
        self.GroupEButton.pack( side=tk.LEFT )

        self.bookNumberVar = tk.StringVar()
        self.bookNumberVar.set( '1' )
        self.maxBooks = len( self.genericBookList )
        #print( "maxChapters", self.maxChaptersThisBook )
        self.bookNumberSpinbox = tk.Spinbox( navigationBar, width=3, from_=1-self.offsetGenesis, to=self.maxBooks, textvariable=self.bookNumberVar )
        #self.bookNumberSpinbox['width'] = 3
        self.bookNumberSpinbox['command'] = self.spinToNewBookNumber
        self.bookNumberSpinbox.bind( '<Return>', self.spinToNewBookNumber )
        self.bookNumberSpinbox.pack( side=tk.LEFT )

        self.bookNames = [self.getGenericBookName(BBB) for BBB in self.genericBookList] # self.getBookList()]
        bookName = self.bookNames[1] # Default to Genesis usually
        self.bookNameVar = tk.StringVar()
        self.bookNameVar.set( bookName )
        BBB = self.getBBBFromText( bookName )
        self.bookNameBox = Combobox( navigationBar, width=len('Deuteronomy'), textvariable=self.bookNameVar )
        self.bookNameBox['values'] = self.bookNames
        #self.bookNameBox['width'] = len( 'Deuteronomy' )
        self.bookNameBox.bind('<<ComboboxSelected>>', self.spinToNewBook )
        self.bookNameBox.bind( '<Return>', self.spinToNewBook )
        self.bookNameBox.pack( side=tk.LEFT )

        self.chapterNumberVar = tk.StringVar()
        self.chapterNumberVar.set( '1' )
        self.maxChaptersThisBook = self.getNumChapters( BBB )
        #print( "maxChapters", self.maxChaptersThisBook )
        self.chapterSpinbox = tk.Spinbox( navigationBar, width=3, from_=0.0, to=self.maxChaptersThisBook, textvariable=self.chapterNumberVar )
        #self.chapterSpinbox['width'] = 3
        self.chapterSpinbox['command'] = self.spinToNewChapter
        self.chapterSpinbox.bind( '<Return>', self.spinToNewChapter )
        self.chapterSpinbox.pack( side=tk.LEFT )

        #self.chapterNumberVar = tk.StringVar()
        #self.chapterNumberVar.set( '1' )
        #self.chapterNumberBox = Entry( self, textvariable=self.chapterNumberVar )
        #self.chapterNumberBox['width'] = 3
        #self.chapterNumberBox.pack()

        self.verseNumberVar = tk.StringVar()
        self.verseNumberVar.set( '1' )
        #self.maxVersesThisChapterVar = tk.StringVar()
        self.maxVersesThisChapter = self.getNumVerses( BBB, self.chapterNumberVar.get() )
        #print( "maxVerses", self.maxVersesThisChapter )
        #self.maxVersesThisChapterVar.set( str(self.maxVersesThisChapter) )
        # Add 1 to maxVerses to enable them to go to the next chapter
        self.verseSpinbox = tk.Spinbox( navigationBar, width=3, from_=0.0, to=1.0+self.maxVersesThisChapter, textvariable=self.verseNumberVar )
        #self.verseSpinbox['width'] = 3
        self.verseSpinbox['command'] = self.acceptNewBnCV
        self.verseSpinbox.bind( '<Return>', self.acceptNewBnCV )
        self.verseSpinbox.pack( side=tk.LEFT )

        #self.verseNumberVar = tk.StringVar()
        #self.verseNumberVar.set( '1' )
        #self.verseNumberBox = Entry( self, textvariable=self.verseNumberVar )
        #self.verseNumberBox['width'] = 3
        #self.verseNumberBox.pack()

        self.wordVar = tk.StringVar()
        if self.lexiconWord: self.wordVar.set( self.lexiconWord )
        self.wordBox = Entry( navigationBar, width=12, textvariable=self.wordVar )
        self.wordBox.bind( '<Return>', self.acceptNewLexiconWord )
        self.wordBox.pack( side=tk.LEFT )

        if 0: # I don't think we should need this button if everything else works right
            self.updateButton = Button( navigationBar, text="Update", command=self.acceptNewBnCV )
            self.updateButton.pack( side=tk.LEFT )

        Style( self ).map("Quit.TButton", foreground=[('pressed', 'red'), ('active', 'blue')],
                                            background=[('pressed', '!disabled', 'black'), ('active', 'pink')] )
        self.quitButton = Button( navigationBar, text="QUIT", style="Quit.TButton", command=self.doCloseMe )
        self.quitButton.pack( side=tk.RIGHT )

        #Sizegrip( self ).grid( column=999, row=999, sticky=(S,E) )
        navigationBar.pack( side=tk.TOP, fill=tk.X )
    # end of Application.createNormalNavigationBar

    def createTouchNavigationBar( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createTouchNavigationBar()") )
            assert self.touchMode

        xPad, yPad = 6, 8
        minButtonCharWidth = 4

        Style().configure('NavigationBar.TFrame', background='yellow')
        navigationBar = Frame( self, cursor='hand2', relief=tk.RAISED, style='NavigationBar.TFrame' )

        self.previousBCVButton = Button( navigationBar, width=minButtonCharWidth, text='<-', command=self.doGoBackward, state=tk.DISABLED )
        self.previousBCVButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )
        self.nextBCVButton = Button( navigationBar, width=minButtonCharWidth, text='->', command=self.doGoForward, state=tk.DISABLED )
        self.nextBCVButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        Style().configure( 'A.TButton', background='lightgreen' )
        Style().configure( 'B.TButton', background='pink' )
        Style().configure( 'C.TButton', background='orange' )
        Style().configure( 'D.TButton', background='brown' )
        self.GroupAButton = Button( navigationBar, width=minButtonCharWidth,
                                   text='A', style='A.TButton', command=self.selectGroupA, state=tk.DISABLED )
        self.GroupBButton = Button( navigationBar, width=minButtonCharWidth,
                                   text='B', style='B.TButton', command=self.selectGroupB, state=tk.DISABLED )
        self.GroupCButton = Button( navigationBar, width=minButtonCharWidth,
                                   text='C', style='C.TButton', command=self.selectGroupC, state=tk.DISABLED )
        self.GroupDButton = Button( navigationBar, width=minButtonCharWidth,
                                   text='D', style='D.TButton', command=self.selectGroupD, state=tk.DISABLED )
        self.GroupEButton = Button( navigationBar, width=minButtonCharWidth,
                                   text='E', style='D.TButton', command=self.selectGroupE, state=tk.DISABLED )
        self.GroupAButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )
        self.GroupBButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )
        self.GroupCButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )
        self.GroupDButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )
        self.GroupEButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        self.bookNumberVar = tk.StringVar()
        self.bookNumberVar.set( '1' )
        self.maxBooks = len( self.genericBookList )
        #print( "maxChapters", self.maxChaptersThisBook )
        self.bookNumberSpinbox = tk.Spinbox( navigationBar, width=3, from_=1-self.offsetGenesis, to=self.maxBooks, textvariable=self.bookNumberVar )
        #self.bookNumberSpinbox['width'] = 3
        self.bookNumberSpinbox['command'] = self.spinToNewBookNumber
        self.bookNumberSpinbox.bind( '<Return>', self.spinToNewBookNumber )
        #self.bookNumberSpinbox.pack( side=tk.LEFT )

        self.bookNames = [self.getGenericBookName(BBB) for BBB in self.genericBookList] # self.getBookList()]
        bookName = self.bookNames[1] # Default to Genesis usually
        self.bookNameVar = tk.StringVar()
        self.bookNameVar.set( bookName )
        BBB = self.getBBBFromText( bookName )
        self.bookNameBox = Combobox( navigationBar, width=len('Deuteronomy'), textvariable=self.bookNameVar )
        self.bookNameBox['values'] = self.bookNames
        #self.bookNameBox['width'] = len( 'Deuteronomy' )
        self.bookNameBox.bind('<<ComboboxSelected>>', self.spinToNewBook )
        self.bookNameBox.bind( '<Return>', self.spinToNewBook )
        #self.bookNameBox.pack( side=tk.LEFT )

        Style().configure( 'bookName.TButton', background='brown' )
        self.bookNameButton = Button( navigationBar, width=8, text=bookName, style='bookName.TButton', command=self.doBookNameButton )
        self.bookNameButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        self.chapterNumberVar = tk.StringVar()
        self.chapterNumberVar.set( '1' )
        self.maxChaptersThisBook = self.getNumChapters( BBB )
        #print( "maxChapters", self.maxChaptersThisBook )
        self.chapterSpinbox = tk.Spinbox( navigationBar, width=3, from_=0.0, to=self.maxChaptersThisBook, textvariable=self.chapterNumberVar )
        #self.chapterSpinbox['width'] = 3
        self.chapterSpinbox['command'] = self.spinToNewChapter
        self.chapterSpinbox.bind( '<Return>', self.spinToNewChapter )
        #self.chapterSpinbox.pack( side=tk.LEFT )

        Style().configure( 'chapterNumber.TButton', background='brown' )
        self.chapterNumberButton = Button( navigationBar, width=minButtonCharWidth, text='1', style='chapterNumber.TButton', command=self.doChapterNumberButton )
        self.chapterNumberButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        #self.chapterNumberVar = tk.StringVar()
        #self.chapterNumberVar.set( '1' )
        #self.chapterNumberBox = Entry( self, textvariable=self.chapterNumberVar )
        #self.chapterNumberBox['width'] = 3
        #self.chapterNumberBox.pack()

        self.verseNumberVar = tk.StringVar()
        self.verseNumberVar.set( '1' )
        #self.maxVersesThisChapterVar = tk.StringVar()
        self.maxVersesThisChapter = self.getNumVerses( BBB, self.chapterNumberVar.get() )
        #print( "maxVerses", self.maxVersesThisChapter )
        #self.maxVersesThisChapterVar.set( str(self.maxVersesThisChapter) )
        # Add 1 to maxVerses to enable them to go to the next chapter
        self.verseSpinbox = tk.Spinbox( navigationBar, width=3, from_=0.0, to=1.0+self.maxVersesThisChapter, textvariable=self.verseNumberVar )
        #self.verseSpinbox['width'] = 3
        self.verseSpinbox['command'] = self.acceptNewBnCV
        self.verseSpinbox.bind( '<Return>', self.acceptNewBnCV )
        #self.verseSpinbox.pack( side=tk.LEFT )

        Style().configure( 'verseNumber.TButton', background='brown' )
        self.verseNumberButton = Button( navigationBar, width=minButtonCharWidth, text='1', style='verseNumber.TButton', command=self.doVerseNumberButton )
        self.verseNumberButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        self.wordVar = tk.StringVar()
        if self.lexiconWord: self.wordVar.set( self.lexiconWord )
        self.wordBox = Entry( navigationBar, width=12, textvariable=self.wordVar )
        #self.wordBox['width'] = 12
        self.wordBox.bind( '<Return>', self.acceptNewLexiconWord )
        #self.wordBox.pack( side=tk.LEFT )

        Style().configure( 'word.TButton', background='brown' )
        self.wordButton = Button( navigationBar, width=8, text=self.lexiconWord, style='word.TButton', command=self.doWordButton )
        self.wordButton.pack( side=tk.LEFT, padx=xPad, pady=yPad )

        if 0: # I don't think we should need this button if everything else works right
            self.updateButton = Button( navigationBar )
            self.updateButton['text'] = 'Update'
            self.updateButton['command'] = self.acceptNewBnCV
            #self.updateButton.grid( row=0, column=7 )
            self.updateButton.pack( side=tk.LEFT )

        Style( self ).map("Quit.TButton", foreground=[('pressed', 'red'), ('active', 'blue')],
                                            background=[('pressed', '!disabled', 'black'), ('active', 'pink')] )
        self.quitButton = Button( navigationBar, text=_("QUIT"), style="Quit.TButton", command=self.doCloseMe )
        self.quitButton.pack( side=tk.RIGHT, padx=xPad, pady=yPad )

        #Sizegrip( self ).grid( column=999, row=999, sticky=(S,E) )
        navigationBar.pack( side=tk.TOP, fill=tk.X )
    # end of Application.createTouchNavigationBar


    def createToolBar( self ):
        """
        Create a tool bar containing several helpful buttons at the top of the main window.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createToolBar()") )

        xPad, yPad = (6, 8) if self.touchMode else (4, 4)

        Style().configure( 'ToolBar.TFrame', background='khaki1' )
        toolbar = Frame( self, cursor='hand2', relief=tk.RAISED, style='ToolBar.TFrame' )

        Style().configure( 'ShowAll.TButton', background='lightGreen' )
        Style().configure( 'HideResources.TButton', background='lightBlue' )
        Style().configure( 'HideProjects.TButton', background='pink' )
        Style().configure( 'HideAll.TButton', background='orange' )
        Style().configure( 'SaveAll.TButton', background='royalBlue1' )

        Button( toolbar, text=_("Show All"), style='ShowAll.TButton', command=self.doShowAll ) \
                    .pack( side=tk.LEFT, padx=xPad, pady=yPad )
        Button( toolbar, text=_("Hide Resources"), style='HideResources.TButton', command=self.doHideAllResources ) \
                    .pack( side=tk.LEFT, padx=xPad, pady=yPad )
        Button( toolbar, text=_("Hide Projects"), style='HideProjects.TButton', command=self.doHideAllProjects ) \
                    .pack( side=tk.LEFT, padx=xPad, pady=yPad )
        Button( toolbar, text=_("Hide All"), style='HideAll.TButton', command=self.doHideAll ) \
                    .pack( side=tk.LEFT, padx=xPad, pady=yPad )
        Button( toolbar, text=_("Save All"), style='SaveAll.TButton', command=self.doSaveAll ) \
                    .pack( side=tk.RIGHT, padx=xPad, pady=yPad )
        #Button( toolbar, text=_("Bring All"), command=self.doBringAll ).pack( side=tk.LEFT, padx=2, pady=2 )

        toolbar.pack( side=tk.TOP, fill=tk.X )
    # end of Application.createToolBar


    def halt( self ):
        """
        Halts the program immediately without saving any files or settings.
        Only used in debug mode.
        """
        logging.critical( "User selected HALT in DEBUG MODE. Not saving any files or settings!" )
        self.quit()
    # end of Application.halt


    def createDebugToolBar( self ):
        """
        Create a debug tool bar containing several additional buttons at the top of the main window.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createDebugToolBar()") )

        xPad, yPad = (6, 8) if self.touchMode else (2, 2)

        Style().configure( 'DebugToolBar.TFrame', background='red' )
        Style().map("Halt.TButton", foreground=[('pressed', 'red'), ('active', 'yellow')],
                                            background=[('pressed', '!disabled', 'black'), ('active', 'pink')] )

        toolbar = Frame( self, cursor='hand2', relief=tk.RAISED, style='DebugToolBar.TFrame' )
        Button( toolbar, text='Halt', style='Halt.TButton', command=self.halt ) \
                        .pack( side=tk.RIGHT, padx=xPad, pady=yPad )
        Button( toolbar, text='Save settings', command=lambda: writeSettingsFile(self) ) \
                        .pack( side=tk.RIGHT, padx=xPad, pady=yPad )
        toolbar.pack( side=tk.TOP, fill=tk.X )
    # end of Application.createDebugToolBar


    def createStatusBar( self ):
        """
        Create a status bar containing only one text label at the bottom of the main window.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createStatusBar()") )

        #Style().configure( 'MainStatusBar.TLabel', background='pink' )
        #Style().configure( 'MainStatusBar.TLabel', background='DarkOrange1' )
        Style().configure( 'MainStatusBar.TLabel', background='forest green' )

        self.statusTextVariable = tk.StringVar()
        self.statusTextLabel = Label( self.rootWindow, relief=tk.SUNKEN,
                                    textvariable=self.statusTextVariable, style='MainStatusBar.TLabel' )
                                    #, font=('arial',16,tk.NORMAL) )
        self.statusTextLabel.pack( side=tk.BOTTOM, fill=tk.X )
        self.statusTextVariable.set( '' ) # first initial value
        self.setWaitStatus( _("Starting up…") )
    # end of Application.createStatusBar


    def createMainKeyboardBindings( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("createMainKeyboardBindings()") )

        self.myKeyboardBindingsList = []
        for name,command in ( ('Help',self.doHelp), ('About',self.doAbout), ('Quit',self.doCloseMe) ):
            if name in self.keyBindingDict:
                for keyCode in self.keyBindingDict[name][1:]:
                    #print( "Bind {} for {}".format( repr(keyCode), repr(name) ) )
                    self.rootWindow.bind( keyCode, command )
                self.myKeyboardBindingsList.append( (name,self.keyBindingDict[name][0],) )
            else: logging.critical( 'No key binding available for {!r}'.format( name ) )

        # These bindings apply to/from all windows
        self.bind_all( '<Alt-Up>', self.doGotoPreviousVerse )
        self.bind_all( '<Alt-Down>', self.doGotoNextVerse )
        self.bind_all( '<Alt-comma>', self.doGotoPreviousChapter )
        self.bind_all( '<Alt-period>', self.doGotoNextChapter )
        self.bind_all( '<Alt-bracketleft>', self.doGotoPreviousBook )
        self.bind_all( '<Alt-bracketright>', self.doGotoNextBook )
    # end of Application.createMainKeyboardBindings()


    def addRecentFile( self, threeTuple ):
        """
        Puts most recent first
        """
        self.logUsage( ProgName, debuggingThisModule, 'addRecentFile {}'.format( threeTuple ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("addRecentFile( {} )").format( threeTuple ) )
            assert len(threeTuple) == 3

        try: self.recentFiles.remove( threeTuple ) # Remove a duplicate if present
        except ValueError: pass
        self.recentFiles.insert( 0, threeTuple ) # Put this one at the beginning of the lis
        if len(self.recentFiles)>MAX_RECENT_FILES: self.recentFiles.pop() # Remove the last one if necessary
        self.createNormalMenuBar()
    # end of Application.addRecentFile()


    def notWrittenYet( self ):
        errorBeep()
        showerror( self, _("Not implemented"), _("Not yet available, sorry") )
    # end of Application.notWrittenYet


    def getVerseKey( self, groupCode ):
        """
        Given a groupCode (A..E), return the appropriate verseKey.
        """
        assert groupCode in BIBLE_GROUP_CODES

        if   groupCode == 'A': return self.GroupA_VerseKey
        elif groupCode == 'B': return self.GroupB_VerseKey
        elif groupCode == 'C': return self.GroupC_VerseKey
        elif groupCode == 'D': return self.GroupD_VerseKey
        elif groupCode == 'E': return self.GroupE_VerseKey
        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
    # end of Application.getVerseKey


    def setStatus( self, newStatusText='' ):
        """
        Set (or clear) the status bar text.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setStatus( {!r} )").format( newStatusText ) )

        #print( "SB is", repr( self.statusTextVariable.get() ) )
        if newStatusText != self.statusTextVariable.get(): # it's changed
            #self.statusBarTextWidget.configure( state=tk.NORMAL )
            #self.statusBarTextWidget.delete( START, tk.END )
            #if newStatusText:
                #self.statusBarTextWidget.insert( START, newStatusText )
            #self.statusBarTextWidget.configure( state=tk.DISABLED ) # Don't allow editing
            #self.statusText = newStatusText
            Style().configure( 'MainStatusBar.TLabel', foreground='white', background='purple' )
            self.statusTextVariable.set( newStatusText )
            self.statusTextLabel.update()
    # end of Application.setStatus

    def setErrorStatus( self, newStatusText ):
        """
        Set the status bar text and change the cursor to the wait/hourglass cursor.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setErrorStatus( {!r} )").format( newStatusText ) )

        #self.rootWindow.configure( cursor='watch' ) # 'wait' can only be used on Windows
        #self.statusTextLabel.configure( style='MainStatusBar.TLabelWait' )
        self.setStatus( newStatusText )
        Style().configure( 'MainStatusBar.TLabel', foreground='yellow', background='red' )
        self.update()
    # end of Application.setErrorStatus

    def setWaitStatus( self, newStatusText ):
        """
        Set the status bar text and change the cursor to the wait/hourglass cursor.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setWaitStatus( {!r} )").format( newStatusText ) )

        self.rootWindow.configure( cursor='watch' ) # 'wait' can only be used on Windows
        #self.statusTextLabel.configure( style='MainStatusBar.TLabelWait' )
        self.setStatus( newStatusText )
        Style().configure( 'MainStatusBar.TLabel', foreground='black', background='DarkOrange1' )
        self.update()
    # end of Application.setWaitStatus

    def setReadyStatus( self ):
        """
        Sets the status line to "Ready"
            and sets the cursor to the normal cursor
        unless we're still starting
            (this covers any slow start-up functions that don't yet set helpful statuses)
        """
        if self.starting: self.setWaitStatus( _("Starting up…") )
        else: # we really are ready
            #self.statusTextLabel.configure( style='MainStatusBar.TLabelReady' )
            self.setStatus( _("Ready") )
            Style().configure( 'MainStatusBar.TLabel', foreground='yellow', background='forest green' )
            self.configure( cursor='' )
    # end of Application.setReadyStatus


    def setDebugText( self, newMessage=None ):
        """
        """
        if debuggingThisModule:
            #print( exp("setDebugText( {!r} )").format( newMessage ) )
            assert BibleOrgSysGlobals.debugFlag

        logging.info( 'Debug: ' + newMessage ) # Not sure why logging.debug isn't going into the file! XXXXXXXXXXXXX
        self.debugTextBox.configure( state=tk.NORMAL ) # Allow editing
        self.debugTextBox.delete( START, tk.END ) # Clear everything
        self.debugTextBox.insert( tk.END, 'DEBUGGING INFORMATION:' )
        if self.lastDebugMessage: self.debugTextBox.insert( tk.END, '\nWas: ' + self.lastDebugMessage )
        if newMessage:
            self.debugTextBox.insert( tk.END, '\n' )
            self.debugTextBox.insert( tk.END, 'Msg: ' + newMessage, 'emp' )
            self.lastDebugMessage = newMessage
        self.debugTextBox.insert( tk.END, '\n\n{} child windows:'.format( len(self.childWindows) ) )
        for j, appWin in enumerate( self.childWindows ):
            #try: extra = ' ({})'.format( appWin.BCVUpdateType )
            #except AttributeError: extra = ''
            self.debugTextBox.insert( tk.END, "\n  {} wT={} gWT={} {} modID={} cVM={} BCV={}" \
                                    .format( j+1,
                                        appWin.windowType,
                                        #appWin.windowType.replace('ChildWindow',''),
                                        appWin.genericWindowType,
                                        #appWin.genericWindowType.replace('Resource',''),
                                        appWin.winfo_geometry(), appWin.moduleID,
                                        appWin._contextViewMode if 'Bible' in appWin.genericWindowType else 'N/A',
                                        appWin.BCVUpdateType if 'Bible' in appWin.genericWindowType else 'N/A' ) )
                                        #extra ) )
        #self.debugTextBox.insert( tk.END, '\n{} resource frames:'.format( len(self.childWindows) ) )
        #for j, projFrame in enumerate( self.childWindows ):
            #self.debugTextBox.insert( tk.END, "\n  {} {}".format( j, projFrame ) )
        self.debugTextBox.configure( state=tk.DISABLED ) # Don't allow editing
    # end of Application.setDebugText


    def doChangeTheme( self, newThemeName ):
        """
        Set the window theme to the given scheme.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doChangeTheme( {!r} )").format( newThemeName ) )
            assert newThemeName
            self.setDebugText( 'Set theme to {!r}'.format( newThemeName ) )

        self.themeName = newThemeName
        try:
            self.style.theme_use( newThemeName )
        except tk.TclError as err:
            showerror( self, 'Error', err )
    # end of Application.doChangeTheme


    def doCheckForMessagesFromDeveloper( self, event=None ):
        """
        Check if there's any new messages on the website from the developer.
        """
        logging.info( exp("Application.doCheckForMessagesFromDeveloper()") )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doCheckForMessagesFromDeveloper()") )

        hadError = False
        import urllib.request
        site = 'Freely-Given.org'
        # NOTE: needs to be https eventually!!!
        indexString = None
        url = 'http://{}/Software/BibleQlator/DevMsg/DevMsg.idx'.format( site )
        try:
            with urllib.request.urlopen( url ) as response:
                indexData = response.read() # a `bytes` object
            #print( "indexData", repr(indexData) )
        except urllib.error.HTTPError as err:
            logging.debug( "doCheckForMessagesFromDeveloper got HTTPError from {}: {}".format( url, err ) )
            hadError = True
        except urllib.error.URLError as err:
            logging.debug( "doCheckForMessagesFromDeveloper got URLError from {}: {}".format( url, err ) )
            hadError = True
        else: indexString = indexData.decode('utf-8')
        #print( "indexString", repr(indexString) )

        #except requests.exceptions.InvalidSchema as err:
            #logging.critical( exp("doCheckForMessagesFromDeveloper: Unable to check for developer messages") )
            #logging.info( exp("doCheckForMessagesFromDeveloper: {}").format( err ) )
            #showerror( self, 'Check for Developer Messages Error', err )
            #return

        if indexString:
            while indexString.endswith( '\n' ): indexString = indexString[:-1] # Removing trailing line feeds
            n,ext = indexString.split( '.', 1 )
            try: ni = int( n )
            except ValueError:
                logging.debug( "doCheckForMessagesFromDeveloper got an unexpected response from {}".format( url ) )
                hadError = True
                #print( 'n', repr(n), 'ext', repr(ext), 'lmnr', self.lastMessageNumberRead )
                ni = -1 # so that nothing at all happens below
            if ni > self.lastMessageNumberRead:
                msgString = None
                url2 = 'http://{}/Software/Biblelator/DevMsg/{}.{}'.format( site, self.lastMessageNumberRead+1, ext )
                #print( 'url2', repr(url2) )
                try:
                    with urllib.request.urlopen( url2 ) as response:
                        msgData = response.read() # a `bytes` object
                        #print( "msgData", repr(msgData) )
                except urllib.error.HTTPError:
                    logging.debug( "doCheckForMessagesFromDeveloper got HTTPError from {}".format( url2 ) )
                    hadError = True
                else: msgString = msgData.decode('utf-8')
                #print( "msgString", repr(msgString) )

                if msgString:
                    from About import AboutBox
                    msgInfo = ProgName + " Message #{} from the Developer".format( self.lastMessageNumberRead+1 )
                    msgInfo += '\n  via {}'.format( site )
                    msgInfo += '\n\n' + msgString
                    ab = AboutBox( self.rootWindow, APP_NAME, msgInfo )

                    self.lastMessageNumberRead += 1

        if hadError:
            print( "doCheckForMessagesFromDeveloper was unable to communicate with the server." )
    # end of Application.doCheckForMessagesFromDeveloper


    #def doSaveNewWindowSetup( self ):
        #"""
        #Gets the name for the new window setup and saves the information.
        #"""
        #saveNewWindowSetup( self )
    ## end of Application.doSaveNewWindowSetup

    #def doDeleteExistingWindowSetup( self ):
        #"""
        #Gets the name of an existing window setting and deletes the setting.
        #"""
        #deleteExistingWindowSetup( self )
    ## end of Application.doDeleteExistingWindowSetup

    #def doApplyNewWindowSetup( self, givenWindowsSettingsName ):
        #"""
        #Gets the name for the new window setup and saves the information.
        #"""
        #applyGivenWindowsSettings( self, givenWindowsSettingsName )
    ## end of Application.doApplyNewWindowSetup



    def doOpenRecent( self, recentIndex ):
        """
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenRecent( {} )").format( recentIndex ) )
            self.setDebugText( "doOpenRecent…" )
            assert recentIndex < len(self.recentFiles)

        filename, folder, windowType = self.recentFiles[recentIndex]
        print( "Need to open", filename, folder, windowType )
        print( "NOT WRITTEN YET" )
    # end of Application.doOpenRecent


    def doOpenDBPBibleResourceWindow( self ):
        """
        Open an online DigitalBiblePlatform Bible (called from a menu/GUI action).

        Requests a version name from the user.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenDBPBibleResourceWindow()") )
            self.setDebugText( "doOpenDBPBibleResourceWindow…" )

        if self.internetAccessEnabled:
            self.setWaitStatus( _("doOpenDBPBibleResourceWindow…") )
            if self.DBPInterface is None:
                self.DBPInterface = DBPBibles()
                availableVolumes = self.DBPInterface.fetchAllEnglishTextVolumes()
                #print( "aV1", repr(availableVolumes) )
                if availableVolumes:
                    srb = SelectResourceBoxDialog( self, [(x,y) for x,y in availableVolumes.items()], title=_('Open DBP resource') )
                    #print( "srbResult", repr(srb.result) )
                    if srb.result:
                        for entry in srb.result:
                            self.openDBPBibleResourceWindow( entry[1] )
                            self.addRecentFile( (entry[1],'','DBPBibleResourceWindow') )
                        #self.acceptNewBnCV()
                        #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
                    elif BibleOrgSysGlobals.debugFlag: print( exp("doOpenDBPBibleResourceWindow: no resource selected!") )
                else:
                    logging.critical( exp("doOpenDBPBibleResourceWindow: no volumes available") )
                    self.setStatus( "Digital Bible Platform unavailable (offline?)" )
        else: # no Internet allowed
            logging.critical( exp("doOpenDBPBibleResourceWindow: Internet not enabled") )
            self.setStatus( "Digital Bible Platform unavailable (You have disabled Internet access.)" )

        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished doOpenDBPBibleResourceWindow" )
    # end of Application.doOpenDBPBibleResourceWindow

    def openDBPBibleResourceWindow( self, moduleAbbreviation, windowGeometry=None ):
        """
        Create the actual requested DBP Bible resource window.

        Returns the new DBPBibleResourceWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openDBPBibleResourceWindow()") )
            self.setDebugText( "openDBPBibleResourceWindow…" )
            assert moduleAbbreviation and isinstance( moduleAbbreviation, str ) and len(moduleAbbreviation)==6

        self.setWaitStatus( _("openDBPBibleResourceWindow…") )
        dBRW = DBPBibleResourceWindow( self, moduleAbbreviation )
        if windowGeometry: dBRW.geometry( windowGeometry )
        if dBRW.DBPModule is None:
            logging.critical( exp("Application.openDBPBibleResourceWindow: Unable to open resource {!r}").format( moduleAbbreviation ) )
            dBRW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open DBP resource") )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed openDBPBibleResourceWindow" )
            self.setReadyStatus()
            return None
        else:
            dBRW.updateShownBCV( self.getVerseKey( dBRW._groupCode ) )
            self.childWindows.append( dBRW )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openDBPBibleResourceWindow" )
            self.setReadyStatus()
            return dBRW
    # end of Application.openDBPBibleResourceWindow


    def doOpenSwordResourceWindow( self ):
        """
        Open a local Sword Bible (called from a menu/GUI action).

        Requests a module abbreviation from the user.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openSwordResource()") )
            self.setDebugText( "doOpenSwordResourceWindow…" )

        self.setWaitStatus( _("doOpenSwordResourceWindow…") )
        if self.SwordInterface is None and SwordType is not None:
            self.SwordInterface = SwordInterface() # Load the Sword library
        if self.SwordInterface is None: # still
            logging.critical( exp("doOpenSwordResourceWindow: no Sword interface available") )
            showerror( self, APP_NAME, _("Sorry, no Sword interface discovered") )
            self.setReadyStatus()
            return

        givenDupleList = self.SwordInterface.getAvailableModuleCodeDuples( ['Biblical Texts','Commentaries'] )
        if not givenDupleList: # try asking for a path
            # Old code
            #gspd = GetSwordPathDialog( self, _("Sword module path") )
            #if gspd.result:
                #self.SwordInterface.augmentModules( gspd.result )
                ## Try again now
                #givenDupleList = self.SwordInterface.getAvailableModuleCodeDuples( ['Biblical Texts','Commentaries'] )
            # New code
            openDialog = Directory( title=_("Select Sword module folder"), initialdir=self.lastSwordDir )
            requestedFolder = openDialog.show()
            if requestedFolder:
                self.lastSwordDir = requestedFolder
                self.SwordInterface.augmentModules( requestedFolder )
                # Try again now
                givenDupleList = self.SwordInterface.getAvailableModuleCodeDuples( ['Biblical Texts','Commentaries'] )
        print( 'givenDupleList', givenDupleList )

        ourList = None
        if givenDupleList:
            genericName = { 'Biblical Texts':'Bible', 'Commentaries':'Commentary' }
            ourList = ['{} ({})'.format(moduleRoughName,genericName[moduleType]) for moduleRoughName,moduleType in givenDupleList]
            if BibleOrgSysGlobals.debugFlag: print( "{} Sword module codes available".format( len(ourList) ) )
        #print( "ourList", ourList )
        if ourList:
            srb = SelectResourceBoxDialog( self, ourList, title=_("Open Sword resource") )
            print( "srbResult", repr(srb.result) )
            if srb.result:
                for entryString in srb.result:
                    requestedModuleName, rest = entryString.split( ' (', 1 )
                    self.setWaitStatus( _("Loading {!r} Sword module…").format( requestedModuleName ) )
                    self.openSwordBibleResourceWindow( requestedModuleName )
                    self.addRecentFile( (requestedModuleName,'','SwordBibleResourceWindow') )
                #self.acceptNewBnCV()
                #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
            elif BibleOrgSysGlobals.debugFlag: print( exp("doOpenSwordResourceWindow: no resource selected!") )
        else:
            logging.critical( exp("doOpenSwordResourceWindow: no list available") )
            showerror( self, APP_NAME, _("Sorry, no Sword resources discovered") )
        #self.acceptNewBnCV()
        #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doOpenSwordResourceWindow

    def openSwordBibleResourceWindow( self, moduleAbbreviation, windowGeometry=None ):
        """
        Create the actual requested Sword Bible resource window.

        Returns the new SwordBibleResourceWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openSwordBibleResourceWindow( {}, {} )").format( moduleAbbreviation, windowGeometry ) )
            self.setDebugText( "openSwordBibleResourceWindow…" )

        self.setWaitStatus( _("openSwordBibleResourceWindow…") )
        if self.SwordInterface is None:
            self.SwordInterface = SwordInterface() # Load the Sword library
        try:
            swBRW = SwordBibleResourceWindow( self, moduleAbbreviation )
        except KeyError: # maybe we need to augment the path ???
            self.SwordInterface.augmentModules( self.lastSwordDir )
            swBRW = SwordBibleResourceWindow( self, moduleAbbreviation )
        if windowGeometry: swBRW.geometry( windowGeometry )
        swBRW.updateShownBCV( self.getVerseKey( swBRW._groupCode ) )
        self.childWindows.append( swBRW )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openSwordBibleResourceWindow" )
        self.setReadyStatus()
        return swBRW
    # end of Application.openSwordBibleResourceWindow


    def doOpenInternalBibleResourceWindow( self ):
        """
        Open a local Bible (called from a menu/GUI action).

        Requests a folder from the user.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openInternalBibleResource()") )
            self.setDebugText( "doOpenInternalBibleResourceWindow…" )

        self.setWaitStatus( _("doOpenInternalBibleResourceWindow…") )
        #requestedFolder = askdirectory()
        openDialog = Directory( title=_("Select Bible folder"), initialdir=self.lastInternalBibleDir )
        requestedFolder = openDialog.show()
        if requestedFolder:
            self.lastInternalBibleDir = requestedFolder
            self.openInternalBibleResourceWindow( requestedFolder )
            self.addRecentFile( (requestedFolder,requestedFolder,'InternalBibleResourceWindow') )
            #self.acceptNewBnCV()
            #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doOpenInternalBibleResourceWindow

    def openInternalBibleResourceWindow( self, modulePath, windowGeometry=None ):
        """
        Create the actual requested local/internal Bible resource window.

        Returns the new InternalBibleResourceWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openInternalBibleResourceWindow()") )
            self.setDebugText( "openInternalBibleResourceWindow…" )

        self.setWaitStatus( _("openInternalBibleResourceWindow…") )
        iBRW = InternalBibleResourceWindow( self, modulePath )
        if windowGeometry: iBRW.geometry( windowGeometry )
        if iBRW.internalBible is None:
            logging.critical( exp("Application.openInternalBibleResourceWindow: Unable to open resource {!r}").format( modulePath ) )
            iBRW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open internal Bible resource") )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed openInternalBibleResourceWindow" )
            self.setReadyStatus()
            return None
        else:
            iBRW.updateShownBCV( self.getVerseKey( iBRW._groupCode ) )
            self.childWindows.append( iBRW )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openInternalBibleResourceWindow" )
            self.setReadyStatus()
            return iBRW
    # end of Application.openInternalBibleResourceWindow


    def doOpenBibleLexiconResourceWindow( self ):
        """
        Open the Bible lexicon (called from a menu/GUI action).

        Requests a folder from the user.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenBibleLexiconResourceWindow()") )
            self.setDebugText( "doOpenBibleLexiconResourceWindow…" )

        self.setWaitStatus( _("doOpenBibleLexiconResourceWindow…") )
        #requestedFolder = askdirectory()
        #if requestedFolder:
        requestedFolder = None
        self.openBibleLexiconResourceWindow( requestedFolder )
        self.addRecentFile( (requestedFolder,requestedFolder,'BibleLexiconResourceWindow') )
        #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doOpenBibleLexiconResourceWindow

    def openBibleLexiconResourceWindow( self, lexiconPath, windowGeometry=None ):
        """
        Create the actual requested local/internal Bible lexicon resource window.

        Returns the new BibleLexiconResourceWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openBibleLexiconResourceWindow()") )
            self.setDebugText( "openBibleLexiconResourceWindow…" )

        self.setWaitStatus( _("openBibleLexiconResourceWindow…") )
        if lexiconPath is None: lexiconPath = "../"
        bLRW = BibleLexiconResourceWindow( self, lexiconPath )
        if windowGeometry: bLRW.geometry( windowGeometry )
        if bLRW.BibleLexicon is None:
            logging.critical( exp("Application.openBibleLexiconResourceWindow: Unable to open Bible lexicon resource {!r}").format( lexiconPath ) )
            bLRW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open Bible lexicon resource") )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed openBibleLexiconResourceWindow" )
            self.setReadyStatus()
            return None
        else:
            if self.lexiconWord: bLRW.updateLexiconWord( self.lexiconWord )
            self.childWindows.append( bLRW )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openBibleLexiconResourceWindow" )
            self.setReadyStatus()
            return bLRW
    # end of Application.openBibleLexiconResourceWindow


    def doOpenNewBibleResourceCollectionWindow( self ):
        """
        Open a collection of Bible resources (called from a menu/GUI action).
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenNewBibleResourceCollectionWindow()") )
            self.setDebugText( "doOpenNewBibleResourceCollectionWindow…" )

        self.setWaitStatus( _("doOpenNewBibleResourceCollectionWindow…") )
        existingNames = []
        for cw in self.childWindows:
            existingNames.append( cw.moduleID.upper() if cw.moduleID else 'Unknown' )
        gncn = GetNewCollectionNameDialog( self, existingNames, title=_("New Collection Name") )
        if gncn.result:
            self.openBibleResourceCollectionWindow( gncn.result )
            self.addRecentFile( (gncn.result,'','BibleResourceCollectionWindow') )
    # end of Application.doOpenNewBibleResourceCollectionWindow

    def openBibleResourceCollectionWindow( self, collectionName, windowGeometry=None ):
        """
        Create the actual requested local/internal Bible resource collection window.

        Returns the new BibleCollectionWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openBibleResourceCollectionWindow( {!r} )").format( collectionName ) )
            self.setDebugText( "openBibleResourceCollectionWindow…" )

        self.setWaitStatus( _("openBibleResourceCollectionWindow…") )
        BRC = BibleResourceCollectionWindow( self, collectionName )
        if windowGeometry: BRC.geometry( windowGeometry )
        #if BRC.internalBible is None:
        #    logging.critical( exp("Application.openBibleResourceCollection: Unable to open resource {}").format( repr(modulePath) ) )
        #    BRC.closeChildWindow()
        #    showerror( self, APP_NAME, _("Sorry, unable to open internal Bible resource") )
        #    if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed openInternalBibleResourceWindow" )
        #    self.setReadyStatus()
        #    return None
        #else:
        BRC.updateShownBCV( self.getVerseKey( BRC._groupCode ) )
        self.childWindows.append( BRC )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openBibleResourceCollection" )
        self.setReadyStatus()
        return BRC
    # end of Application.openBibleResourceCollectionWindow


    def doOpenBibleReferenceCollection( self ):
        """
        Open a collection of Bible References (called from a menu/GUI action).
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenBibleReferenceCollection()") )
            self.setDebugText( "doOpenBibleReferenceCollection…" )

        self.setWaitStatus( _("doOpenBibleReferenceCollection…") )
        existingNames = []
        for cw in self.childWindows:
            existingNames.append( cw.moduleID.upper() )
        gncn = GetNewCollectionNameDialog( self, existingNames, title=_("New Collection Name") )
        if gncn.result:
            self.openBibleReferenceCollectionWindow( gncn.result )
            self.addRecentFile( (gncn.result,'','BibleReferenceCollectionWindow') )
    # end of Application.doOpenBibleReferenceCollection

    def openBibleReferenceCollectionWindow( self, collectionName, windowGeometry=None ):
        """
        Create the actual requested local/internal Bible Reference collection window.

        Returns the new BibleCollectionWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openBibleReferenceCollectionWindow( {!r} )").format( collectionName ) )
            self.setDebugText( "openBibleReferenceCollectionWindow…" )

        self.setWaitStatus( _("openBibleReferenceCollectionWindow…") )
        BRC = BibleReferenceCollectionWindow( self, collectionName )
        if windowGeometry: BRC.geometry( windowGeometry )
        #if BRC.internalBible is None:
        #    logging.critical( exp("Application.openBibleReferenceCollection: Unable to open Reference {}").format( repr(modulePath) ) )
        #    BRC.closeChildWindow()
        #    showerror( self, APP_NAME, _("Sorry, unable to open internal Bible Reference") )
        #    if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed openInternalBibleReferenceWindow" )
        #    self.setReadyStatus()
        #    return None
        #else:
        BRC.updateShownReferences( mapReferencesVerseKey( self.getVerseKey( BIBLE_GROUP_CODES[0] ) ) )
        self.childWindows.append( BRC )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openBibleReferenceCollection" )
        self.setReadyStatus()
        return BRC
    # end of Application.openBibleReferenceCollectionWindow


    def doOpenNewTextEditWindow( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenNewTextEditWindow()") )
            self.setDebugText( "doOpenNewTextEditWindow…" )

        self.setWaitStatus( _("doOpenNewTextEditWindow…") )
        tEW = TextEditWindow( self )
        #if windowGeometry: tEW.geometry( windowGeometry )
        self.childWindows.append( tEW )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished doOpenNewTextEditWindow" )
        self.setReadyStatus()
    # end of Application.doOpenNewTextEditWindow


    def doOpenFileTextEditWindow( self ):
        """
        Open a pop-up window and request the user to select a file.

        Then open the file in a plain text edit window.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doOpenFileTextEditWindow()") )
            self.setDebugText( "doOpenFileTextEditWindow…" )

        self.setWaitStatus( _("doOpenFileTextEditWindow…") )
        openDialog = Open( title=_("Select text file"), initialdir=self.lastFileDir, filetypes=TEXT_FILETYPES )
        fileResult = openDialog.show()
        if not fileResult:
            self.setReadyStatus()
            return
        if not os.path.isfile( fileResult ):
            showerror( self, APP_NAME, 'Could not open file ' + fileResult )
            self.setReadyStatus()
            return

        folderPath = os.path.split( fileResult )[0]
        #print( '\n\n\nFP doOpenFileTextEditWindow', repr(folderPath) )
        self.lastFileDir = folderPath

        self.openFileTextEditWindow( fileResult )
    # end of Application.doOpenFileTextEditWindow

    def openFileTextEditWindow( self, filepath, windowGeometry=None ):
        """
        Then open the file in a plain text edit window.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule: print( exp("openFileTextEditWindow( {} )").format( filepath ) )
            self.setDebugText( "openFileTextEditWindow…" )

        self.setWaitStatus( _("openFileTextEditWindow…") )
        if filepath is None: # it's a blank window
            tEW = TextEditWindow( self )
            if windowGeometry: tEW.geometry( windowGeometry )
            self.childWindows.append( tEW )
        else: # open the text file and fill the window
            text = open( filepath, 'rt', encoding='utf-8' ).read()
            if text == None:
                showerror( self, APP_NAME, 'Could not decode and open file ' + filepath )
            else:
                tEW = TextEditWindow( self )
                tEW.setFilepath( filepath )
                tEW.setAllText( text )
                if windowGeometry: tEW.geometry( windowGeometry )
                self.childWindows.append( tEW )
                self.addRecentFile( (filepath,'','TextEditWindow') )

        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openFileTextEditWindow" )
        self.setReadyStatus()
        return tEW
    # end of Application.openFileTextEditWindow


    def doViewWindowsList( self ):
        """
        Open a pop-up text window with a list of all the current windows displayed.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule: print( exp("doViewWindowsList()") )
            self.setDebugText( "doViewWindowsList…" )

        windowsListText = ""
        for j, appWin in enumerate( self.childWindows ):
            #try: extra = ' ({})'.format( appWin.BCVUpdateType )
            #except AttributeError: extra = ''
            windowsListText += "\n  {}/ wT={} gWT={} {} modID={} cVM={} BCV={}" \
                                .format( j+1,
                                    appWin.windowType,
                                    #appWin.windowType.replace('ChildWindow',''),
                                    appWin.genericWindowType,
                                    #appWin.genericWindowType.replace('Resource',''),
                                    appWin.winfo_geometry(), appWin.moduleID,
                                    appWin._contextViewMode if 'Bible' in appWin.genericWindowType else 'N/A',
                                    appWin.BCVUpdateType if 'Bible' in appWin.genericWindowType else 'N/A' )
                                        #extra )
        print( "windowsListText", windowsListText )
    # end of Application.doViewWindowsList


    def doViewBiblesList( self ):
        """
        Open a pop-up text window with a list of all the current Bibles displayed.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule: print( exp("doViewBiblesList()") )
            self.setDebugText( "doViewBiblesList…" )

        BiblesListText = ""
        #for something in self.internalBibles:
            #print( "  ", something )
            #BiblesListText += "\n{}".format( something )
        #print( self.internalBibles )
        for j,(iB,cWs) in enumerate( self.internalBibles ):
            BiblesListText += "\n  {}/ {} in {}".format( j+1, iB.getAName(), cWs )
            BiblesListText += "\n      {!r} {!r} {!r} {!r}".format( iB.name, iB.givenName, iB.shortName, iB.abbreviation )
            BiblesListText += "\n      {!r} {!r} {!r} {!r}".format( iB.sourceFolder, iB.sourceFilename, iB.sourceFilepath, iB.fileExtension )
            BiblesListText += "\n      {!r} {!r} {!r} {!r}".format( iB.status, iB.revision, iB.version, iB.encoding )
        print( "BiblesListText", BiblesListText )
    # end of Application.doViewBiblesList


    def doViewSettings( self ):
        """
        Open a pop-up text window with the current settings displayed.
        """
        viewSettings( self ) # In BiblelatorSettingsFunctions
    # end of Application.doViewSettings


    def doViewLog( self ):
        """
        Open a pop-up text window with the current log displayed.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule: print( exp("doViewLog()") )
            self.setDebugText( "doViewLog…" )

        self.setWaitStatus( _("doViewLog…") )
        filename = APP_NAME.replace('/','-').replace(':','_').replace('\\','_') + '_log.txt'
        tEW = TextEditWindow( self )
        #if windowGeometry: tEW.geometry( windowGeometry )
        if not tEW.setPathAndFile( self.loggingFolderPath, filename ) \
        or not tEW.loadText():
            tEW.closeChildWindow()
            showerror( self, APP_NAME, _("Sorry, unable to open log file") )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Failed doViewLog" )
        else:
            self.childWindows.append( tEW )
            #if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished doViewLog" ) # Don't do this -- adds to the log immediately
        self.setReadyStatus()
    # end of Application.doViewLog


    def doStartNewProject( self ):
        """
        Asks the user for a project name and abbreviation,
            creates the new folder,
            offers to create blank books,
        and then opens an editor window.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doStartNewProject()") )

        self.setWaitStatus( _("doStartNewProject…") )
        gnpn = GetNewProjectNameDialog( self, title=_("New Project Name") )
        if not gnpn.result:
            self.setReadyStatus()
            return
        if gnpn.result: # This is a dictionary
            projName, projAbbrev = gnpn.result['Name'], gnpn.result['Abbreviation']
            newFolderPath = os.path.join( self.homeFolderPath, DATA_FOLDER_NAME, projAbbrev )
            print( '\n\n\nFP doStartNewProject', repr(newFolderPath) )
            if os.path.isdir( newFolderPath ):
                showerror( self, _("New Project"), _("Sorry, we already have a {!r} project folder in {}") \
                                            .format( projAbbrev, os.path.join( self.homeFolderPath, DATA_FOLDER_NAME ) ) )
                self.setReadyStatus()
                return None
            os.mkdir( newFolderPath )

            #availableVersifications = ['KJV',]
            bvss = BibleVersificationSystems().loadData() # Doesn't reload the XML unnecessarily :)
            availableVersifications = bvss.getAvailableVersificationSystemNames()
            thisBBB = self.getVerseKey( BIBLE_GROUP_CODES[0] ).getBBB() # New windows start in group 0
            cnpf = CreateNewProjectFilesDialog( self, _("Create blank {} files").format( projAbbrev ),
                                thisBBB, availableVersifications )
            #if not cnpf.result: return
            if cnpf.result: # This is a dictionary
                print( "Dialog results:", cnpf.result )
                if cnpf.result['Fill'] == 'Version': # Need to find a USFM project to copy
                    openDialog = Directory( title=_("Select USFM folder"), initialdir=self.lastInternalBibleDir )
                    requestedFolder = openDialog.show()
                    if requestedFolder:
                        self.lastInternalBibleDir = requestedFolder
                        cnpf.result['Version'] = requestedFolder
                    #else: return
                createEmptyUSFMBooks( newFolderPath, thisBBB, cnpf.result )

            uB = USFMBible( newFolderPath ) # Get a blank object
            uB.name, uB.abbreviation = projName, projAbbrev
            uEW = USFMEditWindow( self, uB )
            uEW.windowType = 'BiblelatorUSFMBibleEditWindow' # override the default
            uEW.moduleID = newFolderPath
            uEW.setFolderPath( newFolderPath )
            uEW.settings = ProjectSettings( newFolderPath )
            uEW.settings.saveNameAndAbbreviation( projName, projAbbrev )
            if cnpf.result: uEW.settings.saveNewBookSettings( cnpf.result )
            uEW.updateShownBCV( self.getVerseKey( uEW._groupCode ) )
            self.childWindows.append( uEW )
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished doStartNewProject" )
            self.setReadyStatus()
            return uEW
    # end of Application.doStartNewProject


    def doOpenBiblelatorProject( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doOpenBiblelatorProject()") )
            self.setDebugText( "doOpenBiblelatorProject…" )

        self.setWaitStatus( _("doOpenBiblelatorProject…") )
        openDialog = Open( title=_("Select project settings file"), initialdir=self.lastBiblelatorFileDir, filetypes=BIBLELATOR_PROJECT_FILETYPES )
        projectSettingsFilepath = openDialog.show()
        if not projectSettingsFilepath:
            self.setReadyStatus()
            return
        if not os.path.isfile( projectSettingsFilepath ):
            showerror( self, APP_NAME, 'Could not open file ' + projectSettingsFilepath )
            self.setReadyStatus()
            return
        containingFolderPath, settingsFilename = os.path.split( projectSettingsFilepath )
        print( '\n\n\nFP doOpenBiblelatorProject', repr(containingFolderPath) )
        if BibleOrgSysGlobals.debugFlag: assert settingsFilename == 'ProjectSettings.ini'
        self.openBiblelatorBibleEditWindow( containingFolderPath )
        self.addRecentFile( (containingFolderPath,containingFolderPath,'BiblelatorBibleEditWindow') )
    # end of Application.doOpenBiblelatorProject

    def openBiblelatorBibleEditWindow( self, projectFolderPath, editMode=None, windowGeometry=None ):
        """
        Create the actual requested local Biblelator Bible project window.

        Returns the new USFMEditWindow object.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("openBiblelatorBibleEditWindow( {!r} )").format( projectFolderPath ) )
            self.setDebugText( "openBiblelatorBibleEditWindow…" )
            assert os.path.isdir( projectFolderPath )

        self.setWaitStatus( _("openBiblelatorBibleEditWindow…") )
        uB = USFMBible( projectFolderPath )
        uEW = USFMEditWindow( self, uB, editMode=editMode )
        if windowGeometry: uEW.geometry( windowGeometry )
        uEW.windowType = 'BiblelatorUSFMBibleEditWindow' # override the default
        uEW.moduleID = projectFolderPath
        uEW.setFolderPath( projectFolderPath )
        uEW.settings = ProjectSettings( projectFolderPath )
        uEW.settings.loadUSFMMetadataInto( uB )
        uEW.updateShownBCV( self.getVerseKey( uEW._groupCode ) )
        self.childWindows.append( uEW )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openBiblelatorBibleEditWindow" )
        self.setReadyStatus()
        return uEW
    # end of Application.openBiblelatorBibleEditWindow



    #def doOpenBibleditProject( self ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("doOpenBibleditProject()") )
        #self.notWrittenYet()
    ## end of Application.doOpenBibleditProject


    def doOpenParatextProject( self ):
        """
        Open the Paratext Bible project (called from a menu/GUI action).

        Requests a SSF file from the user.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doOpenParatextProject()") )
            self.setDebugText( "doOpenParatextProject…" )

        self.setWaitStatus( _("doOpenParatextProject…") )
        #if not self.openDialog:
        openDialog = Open( title=_("Select project settings (XML or SSF) file"), initialdir=self.lastParatextFileDir, filetypes=PARATEXT_FILETYPES )
        SSFFilepath = openDialog.show()
        if not SSFFilepath:
            self.setReadyStatus()
            return
        if not os.path.isfile( SSFFilepath ):
            showerror( self, APP_NAME, 'Could not open file ' + SSFFilepath )
            self.setReadyStatus()
            return
        ptxBible = PTX7Bible( None ) # Create a blank Paratext Bible object
        #ptxBible.loadSSFData( SSFFilepath )
        PTXSettingsDict = loadPTX7ProjectData( ptxBible, SSFFilepath )
        if PTXSettingsDict:
            if ptxBible.suppliedMetadata is None: ptxBible.suppliedMetadata = {}
            if 'PTX' not in ptxBible.suppliedMetadata: ptxBible.suppliedMetadata['PTX'] = {}
            ptxBible.suppliedMetadata['PTX']['SSF'] = PTXSettingsDict
            ptxBible.applySuppliedMetadata( 'SSF' ) # Copy some to ptxBible.settingsDict
        #print( "ptx/ssf" )
        #for something in ptxBible.suppliedMetadata['PTX']['SSF']:
            #print( "  ", something, repr(ptxBible.suppliedMetadata['PTX']['SSF'][something]) )
        try: ptxBibleName = ptxBible.suppliedMetadata['PTX']['SSF']['Name']
        except KeyError:
            showerror( self, APP_NAME, "Could not find 'Name' in " + SSFFilepath )
            self.setReadyStatus()
        try: ptxBibleFullName = ptxBible.suppliedMetadata['PTX']['SSF']['FullName']
        except KeyError:
            showerror( self, APP_NAME, "Could not find 'FullName' in " + SSFFilepath )
        if 'Editable' in ptxBible.suppliedMetadata and ptxBible.suppliedMetadata['Editable'] != 'T':
            showerror( self, APP_NAME, 'Project {} ({}) is not set to be editable'.format( ptxBibleName, ptxBibleFullName ) )
            self.setReadyStatus()
            return

        # Find the correct folder that contains the actual USFM files
        if 'Directory' in ptxBible.suppliedMetadata['PTX']['SSF']:
            ssfDirectory = ptxBible.suppliedMetadata['PTX']['SSF']['Directory']
        else:
            showerror( self, APP_NAME, 'Project {} ({}) has no folder specified (bad SSF file?) -- trying folder below SSF'.format( ptxBibleName, ptxBibleFullName ) )
            ssfDirectory = None
        if ssfDirectory is None or not os.path.exists( ssfDirectory ):
            if ssfDirectory is not None:
                showwarning( self, APP_NAME, 'SSF project {} ({}) folder {!r} not found on this system -- trying folder below SSF instead'.format( ptxBibleName, ptxBibleFullName, ssfDirectory ) )
            if not sys.platform.startswith( 'win' ): # Let's try the next folder down
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "doOpenParatextProject: Not MS-Windows" )
                    print( 'doOpenParatextProject: ssD1', repr(ssfDirectory) )
                slash = '\\' if '\\' in ssfDirectory else '/'
                if ssfDirectory[-1] == slash: ssfDirectory = ssfDirectory[:-1] # Remove the trailing slash
                ix = ssfDirectory.rfind( slash ) # Find the last slash
                if ix!= -1:
                    ssfDirectory = os.path.join( os.path.dirname(SSFFilepath), ssfDirectory[ix+1:] + '/' )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'doOpenParatextProject: ssD2', repr(ssfDirectory) )
                    if not os.path.exists( ssfDirectory ):
                        showerror( self, APP_NAME, 'Unable to discover Paratext {} project folder'.format( ptxBibleName ) )
                        return
        self.openParatextBibleEditWindow( SSFFilepath ) # Has to repeat some of the above unfortunately
        self.addRecentFile( (SSFFilepath,SSFFilepath,'ParatextBibleEditWindow') )
    # end of Application.doOpenParatextProject

    def openParatextBibleEditWindow( self, SSFFilepath, editMode=None, windowGeometry=None ):
        """
        Create the actual requested local Paratext Bible project window.

        Returns the new USFMEditWindow object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("openParatextBibleEditWindow( {!r} )").format( SSFFilepath ) )
            self.setDebugText( "openParatextBibleEditWindow…" )
            assert os.path.isfile( SSFFilepath )

        self.setWaitStatus( _("openParatextBibleEditWindow…") )
        ptxBible = PTX7Bible( None ) # Create a blank Paratext Bible object
        PTXSettingsDict = loadPTX7ProjectData( ptxBible, SSFFilepath )
        if PTXSettingsDict:
            if ptxBible.suppliedMetadata is None: ptxBible.suppliedMetadata = {}
            if 'PTX' not in ptxBible.suppliedMetadata: ptxBible.suppliedMetadata['PTX'] = {}
            ptxBible.suppliedMetadata['PTX']['SSF'] = PTXSettingsDict
            ptxBible.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        if 'Directory' in ptxBible.suppliedMetadata['PTX']['SSF']:
            ssfDirectory = ptxBible.suppliedMetadata['PTX']['SSF']['Directory']
        else:
            ssfDirectory = None
        if ssfDirectory is None or not os.path.exists( ssfDirectory ):
            if not sys.platform.startswith( 'win' ): # Let's try the next folder down
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #print( "openParatextBibleEditWindow: Not windows" )
                    #print( 'openParatextBibleEditWindow: ssD1', repr(ssfDirectory) )
                slash = '\\' if '\\' in ssfDirectory else '/'
                if ssfDirectory[-1] == slash: ssfDirectory = ssfDirectory[:-1] # Remove the trailing slash
                ix = ssfDirectory.rfind( slash ) # Find the last slash
                if ix!= -1:
                    ssfDirectory = os.path.join( os.path.dirname(SSFFilepath), ssfDirectory[ix+1:] + '/' )
                    #print( 'ssD2', repr(ssfDirectory) )
        if not os.path.exists( ssfDirectory ):
            showerror( self, APP_NAME, 'Unable to discover Paratext {} project folder'.format( ssfDirectory ) )
            self.setReadyStatus()
            return
        ptxBible.sourceFolder = ptxBible.sourceFilepath = ssfDirectory
        ptxBible.preload()

        uEW = USFMEditWindow( self, ptxBible, editMode=editMode )
        if windowGeometry: uEW.geometry( windowGeometry )
        uEW.windowType = 'ParatextUSFMBibleEditWindow' # override the default
        uEW.moduleID = SSFFilepath
        uEW.setFilepath( SSFFilepath )
        uEW.updateShownBCV( self.getVerseKey( uEW._groupCode ) )
        self.childWindows.append( uEW )
        if uEW.autocompleteMode: uEW.prepareAutocomplete()

        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "Finished openParatextBibleEditWindow" )
        self.setReadyStatus()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("openParatextBibleEditWindow finished.") )
        return uEW
    # end of Application.openParatextBibleEditWindow


    #def doProjectExports( self ):
    #    """
    #    Taking the
    #    """
    ## end of Application.openParatextBibleEditWindow


    def doGoBackward( self, event=None ):
        """
        Used in both desktop and touch modes.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGoBackward( {} )").format( event ) )
            #self.setDebugText( "doGoBackward…" )

        #print( dir(event) )
        assert self.BCVHistory
        assert self.BCVHistoryIndex
        self.BCVHistoryIndex -= 1
        assert self.BCVHistoryIndex >= 0
        self.setCurrentVerseKey( self.BCVHistory[self.BCVHistoryIndex] )
        self.updatePreviousNextButtons()
        #self.acceptNewBnCV()
        self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doGoBackward


    def doGoForward( self, event=None ):
        """
        Used in both desktop and touch modes.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doGoForward( {} )").format( event ) )
            #self.setDebugText( "doGoForward…" )

        #print( dir(event) )
        assert self.BCVHistory
        assert self.BCVHistoryIndex < len(self.BCVHistory)-1
        self.BCVHistoryIndex += 1
        assert self.BCVHistoryIndex < len(self.BCVHistory)
        self.setCurrentVerseKey( self.BCVHistory[self.BCVHistoryIndex] )
        self.updatePreviousNextButtons()
        #self.acceptNewBnCV()
        self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doGoForward


    def doBookNameButton( self, event=None ):
        """
        Used in touch mode.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doBookNameButton( {} )").format( event ) )

        nBBB = self.bookNumberVar.get()
        #BBB = self.bookNumberTable[int(nBBB)]
        bnd = BookNameDialog( self, self.genericBookList, int(nBBB)+self.offsetGenesis-1 )
        #print( "bndResult", repr(bnd.result) )
        if bnd.result is not None:
            self.bookNumberVar.set( bnd.result + 1 - self.offsetGenesis )
            self.spinToNewBookNumber()
        #elif BibleOrgSysGlobals.debugFlag: print( exp("doBookNameButton: no book selected!") )
    # end of Application.doBookNameButton

    def doChapterNumberButton( self, event=None ):
        """
        Used in touch mode.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doChapterNumberButton( {} )").format( event ) )

        C = self.chapterNumberVar.get()
        nbd = NumberButtonDialog( self, 0, self.maxChaptersThisBook, int(C) )
        #print( "C.nbdResult", repr(nbd.result) )
        if nbd.result is not None:
            self.chapterNumberVar.set( nbd.result )
            self.spinToNewChapter()
        #elif BibleOrgSysGlobals.debugFlag: print( exp("doChapterNumberButton: no chapter selected!") )
    # end of Application.doChapterNumberButton

    def doVerseNumberButton( self, event=None ):
        """
        Used in touch mode.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doVerseNumberButton( {} )").format( event ) )

        V = self.verseNumberVar.get()
        nbd = NumberButtonDialog( self, 0, self.maxVersesThisChapter, int(V) )
        #print( "V.nbdResult", repr(nbd.result) )
        if nbd.result is not None:
            self.verseNumberVar.set( nbd.result )
            self.acceptNewBnCV()
        #elif BibleOrgSysGlobals.debugFlag: print( exp("doVerseNumberButton: no chapter selected!") )
    # end of Application.doVerseNumberButton

    def doWordButton( self, event=None ):
        """
        Used in touch mode.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("doWordButton( {} )").format( event ) )

        #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.doWordButton


    def updateBCVGroup( self, newGroupLetter ):
        """
        Change the group to the given one (and then do a acceptNewBnCV)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("updateBCVGroup( {} )").format( newGroupLetter ) )
            self.setDebugText( "updateBCVGroup…" )
            assert newGroupLetter in BIBLE_GROUP_CODES

        self.currentVerseKeyGroup = newGroupLetter
        if   self.currentVerseKeyGroup == 'A': self.currentVerseKey = self.GroupA_VerseKey
        elif self.currentVerseKeyGroup == 'B': self.currentVerseKey = self.GroupB_VerseKey
        elif self.currentVerseKeyGroup == 'C': self.currentVerseKey = self.GroupC_VerseKey
        elif self.currentVerseKeyGroup == 'D': self.currentVerseKey = self.GroupD_VerseKey
        elif self.currentVerseKeyGroup == 'E': self.currentVerseKey = self.GroupE_VerseKey
        else: halt
        if self.currentVerseKey == ('', '1', '1'):
            self.setCurrentVerseKey( SimpleVerseKey( self.getFirstBookCode(), '1', '1' ) )
        self.updateBCVGroupButtons()
        self.setMainWindowTitle()
        self.acceptNewBnCV()
        #self.after_idle( self.acceptNewBnCV ) # Do the acceptNewBnCV once we're idle
    # end of Application.updateBCVGroup


    def updateBCVGroupButtons( self ):
        """
        Updates the display showing the selected group and the selected BCV reference.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("updateBCVGroupButtons()") )
            self.setDebugText( "updateBCVGroupButtons…" )

        groupButtons = [ self.GroupAButton, self.GroupBButton, self.GroupCButton, self.GroupDButton, self.GroupEButton ]
        if   self.currentVerseKeyGroup == 'A': ix = 0
        elif self.currentVerseKeyGroup == 'B': ix = 1
        elif self.currentVerseKeyGroup == 'C': ix = 2
        elif self.currentVerseKeyGroup == 'D': ix = 3
        elif self.currentVerseKeyGroup == 'E': ix = 4
        else: halt
        selectedButton = groupButtons.pop( ix )
        selectedButton.configure( state=tk.DISABLED )#, relief=tk.SUNKEN )
        for otherButton in groupButtons:
            otherButton.configure( state=tk.NORMAL ) #, relief=tk.RAISED )
        self.bookNameVar.set( self.getGenericBookName(self.currentVerseKey[0]) )
        self.chapterNumberVar.set( self.currentVerseKey[1] )
        self.verseNumberVar.set( self.currentVerseKey[2] )
    # end of Application.updateBCVGroupButtons


    def updatePreviousNextButtons( self ):
        """
        Updates the display showing the previous/next buttons as enabled or disabled.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("updatePreviousNextButtons()") )
            self.setDebugText( "updatePreviousNextButtons…" )
        self.previousBCVButton.configure( state=tk.NORMAL if self.BCVHistory and self.BCVHistoryIndex>0 else tk.DISABLED )
        self.nextBCVButton.configure( state=tk.NORMAL if self.BCVHistory and self.BCVHistoryIndex<len(self.BCVHistory)-1 else tk.DISABLED )
    # end of Application.updatePreviousNextButtons


    def selectGroupA( self ):
        self.updateBCVGroup( 'A' )
    # end of Application.selectGroupA
    def selectGroupB( self ):
        self.updateBCVGroup( 'B' )
    # end of Application.selectGroupB
    def selectGroupC( self ):
        self.updateBCVGroup( 'C' )
    # end of Application.selectGroupC
    def selectGroupD( self ):
        self.updateBCVGroup( 'D' )
    # end of Application.selectGroupD
    def selectGroupE( self ):
        self.updateBCVGroup( 'E' )
    # end of Application.selectGroupE


    #def getNumVerses( self, BBB, C ):
        #"""
        #Find the number of verses in this chapter (in the generic BOS)
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("getNumVerses( {}, {} )").format( BBB, C ) )

        #if C=='0' or C==0: return MAX_PSEUDOVERSES
        #try: return self.genericBibleOrganisationalSystem.getNumVerses( BBB, C )
        #except KeyError: return 0
    ## end of Application.getNumVerses


    def doGotoPreviousBook( self, event=None, gotoEnd=False ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousBook( {}, {} ) from {} {}:{}").format( event, gotoEnd, BBB, C, V ) )
            self.setDebugText( "doGotoPreviousBook…" )
        newBBB = self.getPreviousBookCode( BBB )
        if newBBB is None: self.gotoBCV( BBB, '0', '0' )
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, self.maxChaptersThisBook )
            if gotoEnd: self.gotoBCV( newBBB, self.maxChaptersThisBook, self.maxVersesThisChapter )
            else: self.gotoBCV( newBBB, '0', '0' ) # go to the beginning
    # end of Application.doGotoPreviousBook


    def doGotoNextBook( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextBook( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoNextBook…" )
        newBBB = self.getNextBookCode( BBB )
        if newBBB is None: pass # stay just where we are
        else:
            self.maxChaptersThisBook = self.getNumChapters( newBBB )
            self.maxVersesThisChapter = self.getNumVerses( newBBB, '0' )
            self.gotoBCV( newBBB, '0', '0' ) # go to the beginning of the book
    # end of Application.doGotoNextBook


    def doGotoPreviousChapter( self, event=None, gotoEnd=False ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousChapter( {}, {} ) from {} {}:{}").format( event, gotoEnd, BBB, C, V ) )
            self.setDebugText( "doGotoPreviousChapter…" )
        intC, intV = int( C ), int( V )
        if intC > 0:
            self.maxVersesThisChapter = self.getNumVerses( BBB, intC-1 )
            self.gotoBCV( BBB, intC-1, self.getNumVerses( BBB, intC-1 ) if gotoEnd else '0' )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of Application.doGotoPreviousChapter


    def doGotoNextChapter( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextChapter( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoNextChapter…" )
        intC = int( C )
        if intC < self.maxChaptersThisBook:
            self.maxVersesThisChapter = self.getNumVerses( BBB, intC+1 )
            self.gotoBCV( BBB, intC+1, '0' )
        else: self.doGotoNextBook()
    # end of Application.doGotoNextChapter


    def doGotoPreviousVerse( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousVerse( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoPreviousVerse…" )
        intC, intV = int( C ), int( V )
        if intV > 0: self.gotoBCV( BBB, C, intV-1 )
        elif intC > 0: self.doGotoPreviousChapter( gotoEnd=True )
        else: self.doGotoPreviousBook( gotoEnd=True )
    # end of Application.doGotoPreviousVerse


    def doGotoNextVerse( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextVerse( {} ) from {} {}:{} with max {}").format( event, BBB, C, V, self.maxVersesThisChapter ) )
            self.setDebugText( "doGotoNextVerse…" )

        intV = int( V )
        if intV < self.maxVersesThisChapter: self.gotoBCV( BBB, C, intV+1 )
        else: self.doGotoNextChapter()
    # end of Application.doGotoNextVerse


    #def doGoForward( self ):
        #"""
        #"""
        #BBB, C, V = self.currentVerseKey.getBCV()
        #if BibleOrgSysGlobals.debugFlag:
            #print( exp("doGoForward() from {} {}:{}").format( BBB, C, V ) )
            #self.setDebugText( "doGoForward…" )
        #self.notWrittenYet()
    ## end of Application.doGoForward


    #def doGoBackward( self ):
        #"""
        #"""
        #BBB, C, V = self.currentVerseKey.getBCV()
        #if BibleOrgSysGlobals.debugFlag:
            #print( exp("doGoBackward() from {} {}:{}").format( BBB, C, V ) )
            #self.setDebugText( "doGoBackward…" )
        #self.notWrittenYet()
    ## end of Application.doGoBackward


    def doGotoPreviousListItem( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoPreviousListItem( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoPreviousListItem…" )
        self.notWrittenYet()
    # end of Application.doGotoPreviousListItem


    def doGotoNextListItem( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoNextListItem( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoNextListItem…" )
        self.notWrittenYet()
    # end of Application.doGotoNextListItem


    def doGotoBook( self, event=None ):
        """
        """
        BBB, C, V = self.currentVerseKey.getBCV()
        if BibleOrgSysGlobals.debugFlag:
            print( exp("doGotoBook( {} ) from {} {}:{}").format( event, BBB, C, V ) )
            self.setDebugText( "doGotoBook…" )
        self.notWrittenYet()
    # end of Application.doGotoBook


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog giving goto/reference info.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doShowInfo( {} )").format( event ) )

        infoString = 'Current location:\n' \
                 + '  {}\n'.format( self.currentVerseKey.getShortText() ) \
                 + '  {} verses in chapter\n'.format( self.maxVersesThisChapter ) \
                 + '  {} chapters in book\n'.format( "No" if self.maxChaptersThisBook is None else self.maxChaptersThisBook ) \
                 + '\nCurrent references:\n' \
                 + '  A: {}\n'.format( self.GroupA_VerseKey.getShortText() ) \
                 + '  B: {}\n'.format( self.GroupB_VerseKey.getShortText() ) \
                 + '  C: {}\n'.format( self.GroupC_VerseKey.getShortText() ) \
                 + '  D: {}\n'.format( self.GroupD_VerseKey.getShortText() ) \
                 + '  E: {}\n'.format( self.GroupE_VerseKey.getShortText() ) \
                 + '\nBible Organisational System (BOS):\n' \
                 + '  Name: {}\n'.format( self.genericBibleOrganisationalSystem.getOrganizationalSystemName() ) \
                 + '  Versification: {}\n'.format( self.genericBibleOrganisationalSystem.getOrganizationalSystemValue( 'versificationSystem' ) ) \
                 + '  Book Order: {}\n'.format( self.genericBibleOrganisationalSystem.getOrganizationalSystemValue( 'bookOrderSystem' ) ) \
                 + '  Book Names: {}\n'.format( self.genericBibleOrganisationalSystem.getOrganizationalSystemValue( 'punctuationSystem' ) ) \
                 + '  Books: {}'.format( self.genericBibleOrganisationalSystem.getBookList() )
        showinfo( self, 'Goto Information', infoString )
    # end of Application.doShowInfo


    def spinToNewBook( self, event=None ):
        """
        Handle a new book setting from the GUI dropbox.
        """
        self.logUsage( ProgName, debuggingThisModule, 'spinToNewBook' )
        if BibleOrgSysGlobals.debugFlag:
            print( exp("spinToNewBook( {} )").format( event ) )
        #print( dir(event) )

        self.chapterNumberVar.set( '1' )
        self.verseNumberVar.set( '1' )
        self.acceptNewBnCV()
    # end of Application.spinToNewBook


    def spinToNewBookNumber( self, event=None ):
        """
        Handle a new book number setting from the GUI dropbox.
        """
        self.logUsage( ProgName, debuggingThisModule, 'spinToNewBookNumber' )
        if BibleOrgSysGlobals.debugFlag:
            print( exp("spinToNewBookNumber( {} )").format( event ) )
        #print( dir(event) )

        nBBB = self.bookNumberVar.get()
        BBB = self.bookNumberTable[int(nBBB)]
        #print( 'spinToNewBookNumber', repr(nBBB), repr(BBB) )
        self.bookNameVar.set( BBB ) # Will be used by acceptNewBnCV
        self.chapterNumberVar.set( '1' )
        self.verseNumberVar.set( '1' )
        self.acceptNewBnCV()
    # end of Application.spinToNewBookNumber


    def spinToNewChapter( self, event=None ):
        """
        Handle a new chapter setting from the GUI spinbox.
        """
        self.logUsage( ProgName, debuggingThisModule, 'spinToNewChapter' )
        if BibleOrgSysGlobals.debugFlag:
            print( exp("spinToNewChapter( {} )").format( event ) )
        #print( dir(event) )

        #self.chapterNumberVar.set( '1' )
        self.verseNumberVar.set( '1' )
        self.acceptNewBnCV()
    # end of Application.spinToNewChapter


    def acceptNewBnCV( self, event=None ):
        """
        Handle a new bookname, chapter, verse setting from the GUI spinboxes.

        We also allow the user to enter a reference (e.g. "Gn 1:1" into the bookname box).
        """
        enteredBookname = self.bookNameVar.get()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("acceptNewBnCV( {} ) for {!r}").format( event, enteredBookname ) )
            #print( dir(event) )

        BBB, C, V = parseEnteredBookname( enteredBookname, self.currentVerseKey.getBBB(), self.chapterNumberVar.get(), self.verseNumberVar.get(), self.getBBBFromText )
        #enteredBookname = self.bookNameVar.get()
        #C = self.chapterNumberVar.get()
        #V = self.verseNumberVar.get()
        #BBB = self.getBBBFromText( enteredBookname )
        #print( "BBB", BBB )

        if BBB is None:
            self.setErrorStatus( _("Unable to determine book name") )
            self.bookNameBox.focus_set()
        else:
            if BibleOrgSysGlobals.debugFlag: self.setDebugText( "acceptNewBnCV {} {}:{}".format( enteredBookname, C, V ) )
            self.bookNumberVar.set( self.bookNumberTable[BBB] )
            self.bookNameVar.set( self.getGenericBookName(BBB) )
            self.gotoBCV( BBB, C, V )
            self.setReadyStatus()
    # end of Application.acceptNewBnCV


    def haveSwordResourcesOpen( self ):
        """
        """
        #if BibleOrgSysGlobals.debugFlag: print( exp("haveSwordResourcesOpen()") )
        for appWin in self.childWindows:
            if 'Sword' in appWin.windowType:
                if self.SwordInterface is None:
                    self.SwordInterface = SwordInterface() # Load the Sword library
                return True
        return False
    # end of Application.haveSwordResourcesOpen


    #def gotoBnCV( self, enteredBookname, C, V ):
        #"""
        #Converts the bookname to BBB and goes to that new reference.

        #Only alled from acceptNewBnCV.


        #"""
        #if BibleOrgSysGlobals.debugFlag:
            #print( exp("gotoBnCV( {!r} {}:{} )").format( enteredBookname, C, V ) )

        ##self.BnameCV = (enteredBookname,C,V,)
        #BBB = self.getBBBFromText( enteredBookname )
        ##print( "BBB", BBB )
        #if BBB is None:
            #self.setErrorStatus( "Unable to determine book name" )
            #self.bookNameBox.focus_set()
        #else:
            #self.gotoBCV( BBB, C, V )
    ## end of Application.gotoBnCV


    def gotoBCV( self, BBB, C, V, originator=None ):
        """
        Called from acceptNewBnCV also well as many other controls.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("gotoBCV( {} {}:{} {} ) = {} from {}").format( BBB, C, V, originator, self.bookNumberTable[BBB], self.currentVerseKey ) )

        self.setWaitStatus( _("Moving to new Bible reference ({} {}:{})…").format( BBB, C, V ) )
        self.setCurrentVerseKey( SimpleVerseKey( BBB, C, V ) )
        self.update_idletasks() # Try to make the main window respond even before child windows can react
        if BibleOrgSysGlobals.debugFlag:
            if self.bookNumberTable[BBB] > 0: # Preface and stuff might fail this
                assert self.isValidBCVRef( self.currentVerseKey, 'gotoBCV '+str(self.currentVerseKey), extended=True )
        if self.haveSwordResourcesOpen():
            self.SwordKey = self.SwordInterface.makeKey( BBB, C, V )
            #print( "swK", self.SwordKey.getText() )
        self.childWindows.updateThisBibleGroup( self.currentVerseKeyGroup, self.currentVerseKey, originator=originator )
        self.setReadyStatus()
    # end of Application.gotoBCV


    def gotoGroupBCV( self, groupCode, BBB, C, V, originator=None ):
        """
        Sets self.BnameCV and self.currentVerseKey (and if necessary, self.SwordKey)
            then calls update on the child windows.

        Called from child windows.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("gotoGroupBCV( {}, {} {}:{} {} )").format( groupCode, BBB, C, V, originator ) )
            assert groupCode in BIBLE_GROUP_CODES

        newVerseKey = SimpleVerseKey( BBB, C, V )
        if groupCode == self.currentVerseKeyGroup:
            if BibleOrgSysGlobals.debugFlag: assert newVerseKey != self.currentVerseKey
            self.gotoBCV( BBB, C, V, originator=originator )
        else: # it's not the currently selected group
            if   groupCode == 'A': oldVerseKey, self.GroupA_VerseKey = self.GroupA_VerseKey, newVerseKey
            elif groupCode == 'B': oldVerseKey, self.GroupB_VerseKey = self.GroupB_VerseKey, newVerseKey
            elif groupCode == 'C': oldVerseKey, self.GroupC_VerseKey = self.GroupC_VerseKey, newVerseKey
            elif groupCode == 'D': oldVerseKey, self.GroupD_VerseKey = self.GroupD_VerseKey, newVerseKey
            elif groupCode == 'E': oldVerseKey, self.GroupE_VerseKey = self.GroupE_VerseKey, newVerseKey
            else: halt
            if BibleOrgSysGlobals.debugFlag: assert newVerseKey != oldVerseKey # we shouldn't have even been called
            self.childWindows.updateThisBibleGroup( groupCode, newVerseKey, originator=originator )
    # end of Application.gotoGroupBCV


    def setCurrentVerseKey( self, newVerseKey ):
        """
        Called to set the current verse key (and to set the verse key for the current group).

        Then it updates the main GUI spinboxes and our history.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("setCurrentVerseKey( {} )").format( newVerseKey ) )
            #self.setDebugText( "setCurrentVerseKey…" )
            assert isinstance( newVerseKey, SimpleVerseKey )

        self.currentVerseKey = newVerseKey
        if   self.currentVerseKeyGroup == 'A': self.GroupA_VerseKey = self.currentVerseKey
        elif self.currentVerseKeyGroup == 'B': self.GroupB_VerseKey = self.currentVerseKey
        elif self.currentVerseKeyGroup == 'C': self.GroupC_VerseKey = self.currentVerseKey
        elif self.currentVerseKeyGroup == 'D': self.GroupD_VerseKey = self.currentVerseKey
        elif self.currentVerseKeyGroup == 'E': self.GroupE_VerseKey = self.currentVerseKey
        else: halt

        self.updateGUIBCVControls()
    # end of Application.setCurrentVerseKey


    def updateGUIBCVControls( self ):
        """
        Update the book number, book number, and chapter/verse controls/displays
            as well as the history lists

        Uses self.currentVerseKey
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("updateGUIBCVControls()") )
            #self.setDebugText( "updateGUIBCVControls…" )

        BBB, C, V = self.currentVerseKey.getBCV()
        self.maxChaptersThisBook = self.getNumChapters( BBB )
        self.chapterSpinbox['to'] = self.maxChaptersThisBook
        self.maxVersesThisChapter = self.getNumVerses( BBB, C )
        self.verseSpinbox['to'] = self.maxVersesThisChapter

        bookName = self.getGenericBookName( BBB )
        self.bookNameVar.set( bookName )
        self.chapterNumberVar.set( C )
        self.verseNumberVar.set( V )

        if self.touchMode:
            self.bookNameButton['text'] = bookName
            self.chapterNumberButton['text'] = C
            self.verseNumberButton['text'] = V

        if self.currentVerseKey not in self.BCVHistory:
            self.BCVHistoryIndex = len( self.BCVHistory )
            self.BCVHistory.append( self.currentVerseKey )
            self.updatePreviousNextButtons()
    # end of Application.updateGUIBCVControls


    def acceptNewLexiconWord( self, event=None ):
        """
        Handle a new lexicon word setting from the GUI.
        """
        self.logUsage( ProgName, debuggingThisModule, 'acceptNewLexiconWord' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("acceptNewLexiconWord()") )
        #print( dir(event) )

        newWord = self.wordVar.get()
        #print( "Got newWord", repr(newWord) )

        # Adjust the word a bit
        adjWord = newWord.replace( ' ', '' ) # Remove any spaces
        if len(adjWord)>=2 and adjWord[0] in 'GgHh' and adjWord[1:].isdigit():
            adjWord = adjWord[0].upper() + str( int( adjWord[1:] ) ) # Capitalize and remove any leading zeroes
        #print( "Got adjWord", repr(adjWord) )
        if adjWord != newWord: self.wordVar.set( adjWord )

        self.gotoWord( adjWord )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( "acceptNewLexiconWord {}".format( adjWord ) )
        self.setReadyStatus()
    # end of Application.acceptNewLexiconWord


    def gotoWord( self, lexiconWord ):
        """
        Sets self.lexiconWord
            then calls update on the child windows.
        """
        self.logUsage( ProgName, debuggingThisModule, 'gotoWord {!r}'.format( lexiconWord ) )
        if BibleOrgSysGlobals.debugFlag: print( exp("gotoWord( {} )").format( lexiconWord ) )
        assert lexiconWord is None or isinstance( lexiconWord, str )
        self.lexiconWord = lexiconWord
        if self.touchMode: self.wordButton['text'] = lexiconWord
        self.childWindows.updateLexicons( lexiconWord )
    # end of Application.gotoWord


    def doHideAllResources( self ):
        """
        Minimize all of our resource windows,
            i.e., leave the editors and main window
        """
        self.logUsage( ProgName, debuggingThisModule, 'doHideAllResources' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doHideAllResources' )
        self.childWindows.iconifyAll( 'Resource' )
    # end of Application.doHideAllResources

    def doHideAllProjects( self ):
        """
        Minimize all of our resource windows,
            i.e., leave the resources and main window
        """
        self.logUsage( ProgName, debuggingThisModule, 'doHideAllProjects' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doHideAllProjects' )
        self.childWindows.iconifyAll( 'Editor' )
    # end of Application.doHideAllProjects


    def doShowAllResources( self ):
        """
        Show/Restore all of our resource windows,
            i.e., leave the editors and main window
        """
        self.logUsage( ProgName, debuggingThisModule, 'doShowAllResources' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doShowAllResources' )
        self.childWindows.deiconifyAll( 'Resource' )
    # end of Application.doShowAllResources

    def doShowAllProjects( self ):
        """
        Show/Restore all of our project editor windows,
            i.e., leave the resources and main window
        """
        self.logUsage( ProgName, debuggingThisModule, 'doShowAllProjects' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doShowAllProjects' )
        self.childWindows.deiconifyAll( 'Editor' )
    # end of Application.doShowAllProjects


    def doHideAll( self, includeMe=True ):
        """
        Minimize all of our windows.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doHideAll' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doHideAll' )
        self.childWindows.iconifyAll()
        if includeMe: self.rootWindow.iconify()
    # end of Application.doHideAll


    def doShowAll( self ):
        """
        Show/Restore all of our windows.
        """
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doShowAll' )
        self.childWindows.deiconifyAll()
        self.rootWindow.deiconify() # Do this last so it has the focus
        self.rootWindow.lift()
    # end of Application.doShowAll


    def doBringAll( self ):
        """
        Bring all of our windows close.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doBringAll' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doBringAll' )
        x, y = parseWindowGeometry( self.rootWindow.winfo_geometry() )[2:4]
        if x > 30: x = x - 20
        if y > 30: y = y - 20
        for j, win in enumerate( self.childWindows ):
            geometrySet = parseWindowGeometry( win.winfo_geometry() )
            #print( geometrySet )
            newX = x + 10*j
            if newX < 10*j: newX = 10*j
            newY = y + 10*j
            if newY < 10*j: newY = 10*j
            geometrySet[2:4] = newX, newY
            win.geometry( assembleWindowGeometryFromList( geometrySet ) )
        self.doShowAll()
    # end of Application.doBringAll


    def doSaveAll( self ):
        """
        Save any changed files in all of our (edit) windows.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doSaveAll' )
        if BibleOrgSysGlobals.debugFlag: self.setDebugText( 'doSaveAll' )
        self.childWindows.saveAll()
    # end of Application.doSaveAll


    def onGrep( self ):
        """
        new in version 2.1: threaded external file search;
        search matched filenames in directory tree for string;
        tk.Listbox clicks open matched file at line of occurrence;

        search is threaded so the GUI remains active and is not
        blocked, and to allow multiple greps to overlap in time;
        could use threadtools, but avoid loop in no active grep;

        grep Unicode policy: text files content in the searched tree
        might be in any Unicode encoding: we don't ask about each (as
        we do for opens), but allow the encoding used for the entire
        tree to be input, preset it to the platform filesystem or
        text default, and skip files that fail to decode; in worst
        cases, users may need to run grep N times if N encodings might
        exist;  else opens may raise exceptions, and opening in binary
        mode might fail to match encoded text against search string;

        TBD: better to issue an error if any file fails to decode?
        but utf-16 2-bytes/char format created in Notepad may decode
        without error per utf-8, and search strings won't be found;
        TBD: could allow input of multiple encoding names, split on
        comma, try each one for every file, without open loadEncode?
        """
        #from tkinter import Toplevel, StringVar, X, RIDGE, tk.SUNKEN
        #from tkinter.ttk import Label, Entry, Button
        def makeFormRow( parent, label, width=15, browse=True, extend=False ):
            var = tk.StringVar()
            row = Frame(parent)
            lab = Label( row, text=label + '?', relief=tk.RIDGE, width=width)
            ent = Entry( row, textvariable=var) # relief=tk.SUNKEN
            row.pack( fill=tk.X )                                  # uses packed row frames
            lab.pack( side=tk.LEFT )                               # and fixed-width labels
            ent.pack( side=tk.LEFT, expand=tk.YES, fill=tk.X )           # or use grid(row, col)
            if browse:
                btn = Button( row, text='browse…' )
                btn.pack( side=tk.RIGHT )
                if not extend:
                    btn.configure( command=lambda:
                                var.set(askopenfilename() or var.get()) )
                else:
                    btn.configure( command=lambda:
                                var.set( var.get() + ' ' + askopenfilename()) )
            return var
        # end of makeFormRow

        # nonmodal dialog: get dirnname, filenamepatt, grepkey
        popup = tk.Toplevel()
        popup.title( _('PyEdit - grep') )
        var1 = makeFormRow( popup, label=_('Directory root'),   width=18, browse=False)
        var2 = makeFormRow( popup, label=_('Filename pattern'), width=18, browse=False)
        var3 = makeFormRow( popup, label=_('Search string'),    width=18, browse=False)
        var4 = makeFormRow( popup, label=_('Content encoding'), width=18, browse=False)
        var1.set( '.')      # current dir
        var2.set( '*.py')   # initial values
        var4.set( sys.getdefaultencoding() )    # for file content, not filenames
        cb = lambda: self.onDoGrep(var1.get(), var2.get(), var3.get(), var4.get())
        Button( popup, text=_('Go'),command=cb).pack()
    # end of Application.onGrep


    def onDoGrep( self, dirname, filenamepatt, grepkey, encoding):
        """
        on Go in grep dialog: populate scrolled list with matches
        tbd: should producer thread be daemon so it dies with app?
        """
        #from tkinter import Tk
        #from tkinter.ttk import Label
        import threading, queue

        # make non-modal un-closeable dialog
        mypopup = tk.Tk()
        mypopup.title( _('PyEdit - grepping') )
        status = Label( mypopup, text=_('Grep thread searching for: {}…').format( grepkey ) )
        status.pack(padx=20, pady=20)
        mypopup.protocol( 'WM_DELETE_WINDOW', lambda: None)  # ignore X close

        # start producer thread, consumer loop
        myqueue = queue.Queue()
        threadargs = (filenamepatt, dirname, grepkey, encoding, myqueue)
        threading.Thread(target=self.grepThreadProducer, args=threadargs).start()
        self.grepThreadConsumer(grepkey, encoding, myqueue, mypopup)
    # end of Application.onDoGrep


    def grepThreadProducer( self, filenamepatt, dirname, grepkey, encoding, myqueue):
        """
        in a non-GUI parallel thread: queue find.find results list;
        could also queue matches as found, but need to keep window;
        file content and file names may both fail to decode here;

        TBD: could pass encoded bytes to find() to avoid filename
        decoding excs in os.walk/listdir, but which encoding to use:
        sys.getfilesystemencoding() if not None?  see also Chapter6
        footnote issue: 3.1 fnmatch always converts bytes per Latin-1;
        """
        import fnmatch

        def find(pattern, startdir=os.curdir):
            for (thisDir, subsHere, filesHere) in os.walk(startdir):
                for name in subsHere + filesHere:
                    if fnmatch.fnmatch(name, pattern):
                        fullpath = os.path.join(thisDir, name)
                        yield fullpath
        # end of find

        matches = []
        try:
            for filepath in find(pattern=filenamepatt, startdir=dirname):
                try:
                    textfile = open(filepath, encoding=encoding)
                    for (linenum, linestr) in enumerate(textfile):
                        if grepkey in linestr:
                            msg = '%s@%d  [%s]' % (filepath, linenum + 1, linestr)
                            matches.append(msg)
                except UnicodeError as X:
                    print( 'Unicode error in:', filepath, X)       # eg: decode, bom
                except IOError as X:
                    print( 'IO error in:', filepath, X)            # eg: permission
        finally:
            myqueue.put(matches)      # stop consumer loop on find excs: filenames?
    # end of Application.grepThreadProducer


    def grepThreadConsumer( self, grepkey, encoding, myqueue, mypopup):
        """
        in the main GUI thread: watch queue for results or [];
        there may be multiple active grep threads/loops/queues;
        there may be other types of threads/checkers in process,
        especially when PyEdit is attached component (PyMailGUI);
        """
        import queue
        try:
            matches = myqueue.get( block=False )
        except queue.Empty:
            myargs  = (grepkey, encoding, myqueue, mypopup)
            self.after(250, self.grepThreadConsumer, *myargs)
        else:
            mypopup.destroy()     # close status
            self.update()         # erase it now
            if not matches:
                showinfo( self, APP_NAME, 'Grep found no matches for: %r' % grepkey)
            else:
                self.grepMatchesList( matches, grepkey, encoding )
    # end of Application.grepThreadConsumer


    def grepMatchesList( self, matches, grepkey, encoding):
        """
        populate list after successful matches;
        we already know Unicode encoding from the search: use
        it here when filename clicked, so open doesn't ask user;
        """
        #from tkinter import Tk, tk.Listbox, tk.SUNKEN, Y
        from tkinter.ttk import Scrollbar
        class ScrolledList( Frame ):
            def __init__( self, options, parent=None ):
                Frame.__init__( self, parent )
                self.pack( expand=tk.YES, fill=tk.BOTH )                   # make me expandable
                self.makeWidgets(options)

            def handleList(self, event):
                index = self.tk.Listbox.curselection()                # on list double-click
                label = self.tk.Listbox.get(index)                    # fetch selection text
                self.runCommand(label)                             # and call action here
                                                                   # or get(tk.ACTIVE)
            def makeWidgets(self, options):
                sbar = Scrollbar( self )
                matchBox = tk.Listbox( self, relief=tk.SUNKEN )
                sbar.configure( command=matchBox.yview )                    # xlink sbar and list
                matchBox.configure( yscrollcommand=sbar.set )               # move one moves other
                sbar.pack( side=tk.RIGHT, fill=tk.Y )                      # pack first=clip last
                matchBox.pack( side=tk.LEFT, expand=tk.YES, fill=tk.BOTH )        # list clipped first
                pos = 0
                for label in options:                              # add to tk.Listbox
                    matchBox.insert( pos, label )                        # or insert(tk.END,label)
                    pos += 1                                       # or enumerate(options)
               #list.configure(selectmode=SINGLE, setgrid=1)          # select,resize modes
                matchBox.bind('<Double-1>', self.handleList)           # set event handler
                self.tk.Listbox = matchBox

            def runCommand(self, selection):                       # redefine me lower
                print('You selected:', selection)
        # end of class ScrolledList

        print( 'Matches for %s: %s' % (grepkey, len(matches)))

        # catch list double-click
        class ScrolledFilenames(ScrolledList):
            def runCommand( self, selection):
                file, line = selection.split( '  [', 1)[0].split( '@')
                editor = TextEditorMainPopup(
                    loadFirst=file, winTitle=' grep match', loadEncode=encoding)
                editor.onGoto(int(line))
                editor.text.focus_force()   # no, really

        # new non-modal widnow
        popup = tk.Tk()
        popup.title( 'PyEdit - grep matches: %r (%s)' % (grepkey, encoding))
        ScrolledFilenames(parent=popup, options=matches)
    # end of Application.grepMatchesList


    def doOpenSettingsEditor( self, event=None ):
        """
        Display the settings editor window.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doOpenSettingsEditor' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doOpenSettingsEditor( {} )").format( event ) )

        openBiblelatorSettingsEditor( self )
    # end of Application.doOpenSettingsEditor

    def doOpenBOSManager( self, event=None ):
        """
        Display the BOS manager window.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doOpenBOSManager' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doOpenBOSManager( {} )").format( event ) )

        openBOSManager( self )
    # end of Application.doOpenBOSManager

    def doOpenSwordManager( self, event=None ):
        """
        Display the Sword module manager window.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doOpenSwordManager' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doOpenSwordManager( {} )").format( event ) )

        openSwordManager( self )
    # end of Application.doOpenSwordManager


    def logUsage( self, moduleName, debuggingThatModule, usageText ):
        """
        Log usage information for developer to understand typical program use.
        """
        timeString = datetime.now().strftime( '%H:%M')
        if timeString == self.lastLoggedUsageTime: timeString = dateString = None
        else:
            self.lastLoggedUsageTime = timeString
            dateString = datetime.now().strftime( '%Y-%m-%d' )
            if dateString == self.lastLoggedUsageDate: dateString = None
            else: self.lastLoggedUsageDate = dateString

        logText = '{}\n'.format( usageText )

        with open( self.usageLogPath, 'at', encoding='utf-8' ) as logFile: # Append puts the file pointer at the end of the file
            if dateString:
                logFile.write( "\nNew start or new day: {} for {!r} as {!r} on {!r} on {}\n". \
                    format( dateString, self.currentUserName, self.currentUserRole, self.currentProjectName, ProgNameVersion ) )
            if timeString:
                if timeString.endswith( '00' ):
                    logFile.write( "New time: {} for {}\n".format( timeString, dateString ) )
                else: logFile.write( "New time: {}\n".format( timeString ) )
            logFile.write( logText )
    # end of Application.logUsage


    def doHelp( self, event=None ):
        """
        Display a help box.
        """
        from Help import HelpBox
        self.logUsage( ProgName, debuggingThisModule, 'doHelp' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doHelp( {} )").format( event ) )

        helpInfo = ProgNameVersion
        helpInfo += "\n\nBasic instructions:"
        helpInfo += "\n  Use the Resource menu to open study/reference resources."
        helpInfo += "\n  Use the Project menu to open editable Bibles."
        helpInfo += "\n\nKeyboard shortcuts:"
        for name,shortcut in self.myKeyboardBindingsList:
            helpInfo += "\n  {}\t{}".format( name, shortcut )
        helpInfo += "\n\n  {}\t{}".format( 'Prev Verse', 'Alt+UpArrow' )
        helpInfo += "\n  {}\t{}".format( 'Next Verse', 'Alt+DownArrow' )
        helpInfo += "\n  {}\t{}".format( 'Prev Chapter', 'Alt+, (<)' )
        helpInfo += "\n  {}\t{}".format( 'Next Chapter', 'Alt+. (>)' )
        helpInfo += "\n  {}\t{}".format( 'Prev Book', 'Alt+[' )
        helpInfo += "\n  {}\t{}".format( 'Next Book', 'Alt+]' )
        helpImage = 'BiblelatorLogoSmall.gif'
        hb = HelpBox( self.rootWindow, APP_NAME, helpInfo, helpImage )
    # end of Application.doHelp


    def doSubmitBug( self, event=None ):
        """
        Prompt the user to enter a bug report,
            collect other useful settings, etc.,
            and then send it all somewhere.
        """
        from About import AboutBox
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doSubmitBug( {} )").format( event ) )

        if not self.internetAccessEnabled: # we need to warn
            showerror( self, APP_NAME, 'You need to allow Internet access first!' )
            return

        submitInfo = ProgNameVersion
        submitInfo += "\n  This program is not yet finished but we'll add this eventually!"
        ab = AboutBox( self.rootWindow, APP_NAME, submitInfo )
    # end of Application.doSubmitBug


    def doAbout( self, event=None ):
        """
        Display an about box.
        """
        from About import AboutBox
        self.logUsage( ProgName, debuggingThisModule, 'doAbout' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doAbout( {} )").format( event ) )

        aboutInfo = ProgNameVersion
        aboutInfo += "\nA free USFM Bible editor." \
            + "\n\nThis is still an unfinished alpha test version, but it should edit and save your USFM Bible files reliably." \
            + "\n\n{} is written in Python. For more information see our web page at Freely-Given.org/Software/Biblelator".format( ShortProgName )
        aboutImage = 'BiblelatorLogoSmall.gif'
        ab = AboutBox( self.rootWindow, APP_NAME, aboutInfo, aboutImage )
    # end of Application.doAbout


    #def doProjectClose( self ):
        #"""
        #"""
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("doProjectClose()") )
        #self.notWrittenYet()
    ## end of Application.doProjectClose


    #def doWriteSettingsFile( self ):
        #"""
        #Update our program settings and save them.
        #"""
        #writeSettingsFile( self )
    ### end of Application.writeSettingsFile


    def doCloseMyChildWindows( self ):
        """
        Save files first, and then close child windows.
        """
        #self.logUsage( ProgName, debuggingThisModule, 'doCloseMyChildWindows' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doCloseMyChildWindows()") )

        # Try to close edit windows first coz they might have work to save
        for appWin in self.childWindows[:]:
            if 'Editor' in appWin.genericWindowType and appWin.modified():
                appWin.doClose()
                #appWin.onCloseEditor( terminate=False )
                ##if appWin.saveChangesAutomatically: appWin.doSave( 'Auto from app close' )
                ##else: appWin.onCloseEditor()

        # See if they saved/closed them all
        haveModifications = False
        for appWin in self.childWindows:
            if 'Editor' in appWin.genericWindowType and appWin.modified():
                if appWin.modified(): # still???
                    haveModifications = True; break
        if haveModifications:
            showerror( self, _("Save files"), _("You need to save or close your work first.") )
            return False

        # Should be able to close all apps now
        for appWin in self.childWindows[:]:
            appWin.doClose()
        return True
    # end of Application.doCloseMyChildWindows


    def doCloseMe( self ):
        """
        Save files first, and then end the application.
        """
        self.logUsage( ProgName, debuggingThisModule, 'doCloseMe' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("Application.doCloseMe()") )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( _("{} is closing down…").format( APP_NAME ) )

        writeSettingsFile( self )
        if self.doCloseMyChildWindows():
            self.rootWindow.destroy()
        if self.internetAccessEnabled and self.sendUsageStatisticsEnabled:
            try: doSendUsageStatistics( self )
            except: pass # Don't worry too much if something fails in this
    # end of Application.doCloseMe
# end of class Application



def handlePossibleCrash( homeFolderPath, dataFolderName, settingsFolderName ):
    """
    The lock file was still there when we started, so maybe we didn't close cleanly.

    Try to help the user through this problem.
    """
    from collections import OrderedDict
    from USFMBookCompare import USFMBookCompare
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( exp("Application.handlePossibleCrash( {}, {}, {} )").format( homeFolderPath, dataFolderName, settingsFolderName ) )

    print( '\n' + _("Is there another copy of {} already running?").format( APP_NAME ) )
    print( '\n' + _("If not, perhaps {} didn't close nicely (i.e., crashed?) last time?").format( APP_NAME ) )

    iniName = APP_NAME if BibleOrgSysGlobals.commandLineArguments.override is None else BibleOrgSysGlobals.commandLineArguments.override
    if not iniName.lower().endswith( '.ini' ): iniName += '.ini'
    iniFilepath = os.path.join( homeFolderPath, dataFolderName, settingsFolderName, iniName )
    currentWindowDict = OrderedDict()
    with open( iniFilepath, 'rt' ) as iniFile:
        inCurrent = False
        for line in iniFile:
            line = line.strip()
            #while line and line[-1] in '\n\r': line = line[:-1]
            #print( repr(line) )
            if inCurrent:
                if line.startswith( 'window' ):
                    num = line[6]
                    field, contents = line[7:].split( ' = ', 1 )
                    if num not in currentWindowDict: currentWindowDict[num] = {}
                    currentWindowDict[num][field] = contents
                else: inCurrent = False
            elif line == '[WindowSettingCurrent]':
                inCurrent = True
    #print( currentWindowDict )

    hadAny = False
    file1Name, file2Name =  _("Bible file"), _("Autosaved file")
    for num in currentWindowDict:
        if currentWindowDict[num]['Type'] == 'ParatextUSFMBibleEditWindow':
            ssfFilepath = currentWindowDict[num]['SSFFilepath']
            ssfFolder, ssfFilename = os.path.split( ssfFilepath )
            #print( "ssfFolder", ssfFolder )
            ssfName = ssfFilename[:-4]
            print( '  ' + _("Seems you might have been editing {}").format( ssfName ) )
            projectFolder = os.path.join( ssfFolder+'/', ssfName+'/' )
            # Look for an Autosave folder
            autosaveFolderPath = os.path.join( projectFolder, APP_NAME+'/', 'AutoSave/' )
            if os.path.exists( autosaveFolderPath ):
                print( "    " + _("Checking in {}").format( autosaveFolderPath ) )
                for something in os.listdir( autosaveFolderPath ):
                    somepath = os.path.join( autosaveFolderPath, something )
                    #if os.path.isdir( somepath ): foundFolders.append( something )
                    if os.path.isfile( somepath ):
                        filepath = os.path.join( projectFolder, something )
                        if os.path.exists( filepath ):
                            #print( "      Comparing {!r} with {!r}".format( filepath, somepath ) )
                            resultDict = USFMBookCompare( filepath, somepath, file1Name=file1Name, file2Name=file2Name )
                            #print( resultDict )
                            haveSuggestions = False
                            for someKey,someValue in resultDict['Summary'].items():
                                if someValue.startswith( 'file2' ): # autosave file might be important
                                    haveSuggestions = True
                            if haveSuggestions:
                                print( "      " + _("Comparing file1 {}").format( filepath ) )
                                print( "      " + _("     with file2 {}").format( somepath ) )
                                for someKey,someValue in resultDict['Summary'].items():
                                    print( '        {}: {}'.format( someKey, someValue ) )
                                hadAny = True

        elif currentWindowDict[num]['Type'] == 'BiblelatorUSFMBibleEditWindow':
            projectFolder = currentWindowDict[num]['ProjectFolderPath']
            print( '  ' + _("Seems you might have been editing in {}").format( projectFolder ) )
            # Look for an Autosave folder
            autosaveFolderPath = os.path.join( projectFolder, 'AutoSave/' )
            if os.path.exists( autosaveFolderPath ):
                print( "    " + _("Checking in {}").format( autosaveFolderPath ) )
                for something in os.listdir( autosaveFolderPath ):
                    somepath = os.path.join( autosaveFolderPath, something )
                    #if os.path.isdir( somepath ): foundFolders.append( something )
                    if os.path.isfile( somepath ):
                        filepath = os.path.join( projectFolder, something )
                        if os.path.exists( filepath ):
                            #print( "      Comparing {!r} with {!r}".format( filepath, somepath ) )
                            resultDict = USFMBookCompare( filepath, somepath, file1Name=file1Name, file2Name=file2Name )
                            #print( resultDict )
                            haveSuggestions = False
                            for someKey,someValue in resultDict['Summary'].items():
                                if someValue.startswith( 'file2' ): # autosave file might be important
                                    haveSuggestions = True
                            if haveSuggestions:
                                print( "      " + _("Comparing file1 {}").format( filepath ) )
                                print( "      " + _("     with file2 {}").format( somepath ) )
                                for someKey,someValue in resultDict['Summary'].items():
                                    print( '        {}: {}'.format( someKey, someValue ) )
                                hadAny = True
    if hadAny:
        print( '  ' + _("You might want to copy the above AutoSave files???") )
    else: print( '  ' + _("Seems that your files are ok / up-to-date (as far as we can tell)") )

    print( '\n' + _("{} will not open while the lock file exists.").format( APP_NAME ) )
    print( "    " + _("(Remove {!r} from {!r} after backing-up / recovering any files first)").format( LOCK_FILENAME, os.getcwd() ) )
    sys.exit()
# end of handlePossibleCrash



def demo():
    """
    Unattended demo program to handle command line parameters and then run what they want.

    Which windows open depends on the saved settings from the last use.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersionDate )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    tkRootWindow = tk.Tk()
    if BibleOrgSysGlobals.debugFlag:
        print( 'Windowing system is', repr( tkRootWindow.tk.call('tk', 'windowingsystem') ) )
    tkRootWindow.title( ProgNameVersion )

    homeFolderPath = findHomeFolderPath()
    loggingFolderPath = os.path.join( homeFolderPath, DATA_FOLDER_NAME, LOGGING_SUBFOLDER_NAME )
    settings = ApplicationSettings( homeFolderPath, DATA_FOLDER_NAME, SETTINGS_SUBFOLDER_NAME, ProgName )
    settings.load()

    application = Application( tkRootWindow, homeFolderPath, loggingFolderPath, settings )
    # Calls to the window manager class (wm in Tk)
    #application.master.title( ProgNameVersion )
    #application.master.minsize( application.minimumXSize, application.minimumYSize )

    # Program a shutdown
    tkRootWindow.after( 30000, tkRootWindow.destroy ) # Destroy the widget after 30 seconds

    # Start the program running
    tkRootWindow.mainloop()
# end of Biblelator.demo


def main( homeFolderPath, loggingFolderPath ):
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersionDate )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    #print( 'FP main', repr(homeFolderPath), repr(loggingFolderPath) )

    numMyInstancesFound = numParatextInstancesFound = 0
    if sys.platform == 'linux':
        myProcess = subprocess.Popen( ['ps','xa'], stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        programOutputBytes, programErrorOutputBytes = myProcess.communicate()
        #print( 'pob', programOutputBytes, programErrorOutputBytes )
        #returnCode = myProcess.returncode
        programOutputString = programOutputBytes.decode( encoding='utf-8', errors='replace' ) if programOutputBytes else None
        programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors='replace' ) if programErrorOutputBytes else None
        #print( 'linux processes', repr(programOutputString) )
        for line in programOutputString.split( '\n' ):
            # NOTE: Following line assumes that all Python interpreters contain the string 'python'
            if 'python' in line and ProgName+'.py' in line:
                if BibleOrgSysGlobals.debugFlag: print( 'Found in ps xa:', repr(line) )
                numMyInstancesFound += 1
            if 'paratext' in line:
                if BibleOrgSysGlobals.debugFlag: print( 'Found in ps xa:', repr(line) )
                numParatextInstancesFound += 1
        if programErrorOutputString: logging.critical( "ps xa got error: {}".format( programErrorOutputString ) )
    elif sys.platform in ( 'win32', 'win64', ):
        myProcess = subprocess.Popen( ['tasklist.exe','/V'], stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        programOutputBytes, programErrorOutputBytes = myProcess.communicate()
        #print( 'pob', programOutputBytes, programErrorOutputBytes )
        #returnCode = myProcess.returncode
        programOutputString = programOutputBytes.decode( encoding='utf-8', errors='replace' ) if programOutputBytes else None
        programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors='replace' ) if programErrorOutputBytes else None
        #print( 'win processes', repr(programOutputString) )
        for line in programOutputString.split( '\n' ):
            #print( "tasklist line", repr(line) )
            if ProgName+'.py' in line:
                if BibleOrgSysGlobals.debugFlag: print( 'Found in tasklist:', repr(line) )
                # Could possibly check that the line startswith 'cmd.exe' but would need to test that on all Windows versions
                # NOTE: If .py files have an association, 'python.exe' doesn't necessarily appear in the line
                if 'python.exe' in line or not line.startswith( 'notepad' ): # includes Notepad++
                    numMyInstancesFound += 1
            if 'Paratext.exe' in line:
                if BibleOrgSysGlobals.debugFlag: print( 'Found in tasklist:', repr(line) )
                numParatextInstancesFound += 1
        if programErrorOutputString: logging.critical( "tasklist got error: {}".format( programErrorOutputString ) )
    else: logging.critical( _("Don't know how to check for already running instances in {}/{}.").format( sys.platform, os.name ) )
    # Why don't the following work in Windows ???
    if numMyInstancesFound > 1:
        logging.critical( _("Found {} instances of {} running.").format( numMyInstancesFound, ProgName ) )
        try:
            import easygui
        except ImportError:
            result = False
        else: result = easygui.ynbox( _("Seems {} might be already running: Continue?").format( ProgName ),
                                                                ProgNameVersion, ('Yes', 'No'))
        if not result:
            logging.info( "Exiting as user requested." )
            sys.exit()
    if numParatextInstancesFound > 1:
        logging.critical( _("Found {} instances of {} running.").format( numMyInstancesFound, 'Paratext' ) )
        try:
            import easygui
        except ImportError:
            result = False
        else: result = easygui.ynbox( _("Seems {} might be running: Continue?").format( 'Paratext' ),
                                                                ProgNameVersion, ('Yes', 'No'))
        if not result:
            logging.info( "Exiting as user requested." )
            sys.exit()
    #if sys.platform in ( 'win32', 'win64', ):
        #print( "Found", numMyInstancesFound, numParatextInstancesFound )
        #halt

    if os.path.exists( LOCK_FILENAME ): # perhaps the program crashed last time
        handlePossibleCrash( homeFolderPath, DATA_FOLDER_NAME, SETTINGS_SUBFOLDER_NAME )

    # Create the lock file on normal startup
    with open( LOCK_FILENAME, 'wt' ) as lockFile:
        lockFile.write( 'Lock file for {}\n'.format( APP_NAME ) )

    tkRootWindow = tk.Tk()
    if BibleOrgSysGlobals.debugFlag:
        print( 'Windowing system is', repr( tkRootWindow.tk.call('tk', 'windowingsystem') ) ) # e.g., 'x11'

    # Set the window icon and title
    iconImage = tk.PhotoImage( file='Biblelator.gif' )
    tkRootWindow.tk.call( 'wm', 'iconphoto', tkRootWindow._w, iconImage )
    tkRootWindow.title( ProgNameVersion + ' ' + _('starting') + '…' )
    application = Application( tkRootWindow, homeFolderPath, loggingFolderPath, iconImage )
    # Calls to the window manager class (wm in Tk)
    #application.master.title( ProgNameVersion )
    #application.master.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()

    # Remove the lock file when we close
    try: os.remove( LOCK_FILENAME )
    except FileNotFoundError: logging.error( "Seems the Biblelator lock file was already deleted!" )
# end of Biblelator.main


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic set-up
    homeFolderPath = findHomeFolderPath()
    if homeFolderPath[-1] not in '/\\': homeFolderPath += '/'
    loggingFolderPath = os.path.join( homeFolderPath, DATA_FOLDER_NAME, LOGGING_SUBFOLDER_NAME )
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion, loggingFolderPath=loggingFolderPath )
    parser.add_argument( '-o', '--override', type=str, metavar='INIFilename', dest='override', help="override use of Biblelator.ini set-up" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
    #print( BibleOrgSysGlobals.commandLineArguments ); halt
    #if 'win' in sys.platform: # Disable multiprocessing until we get less bugs in Biblelator
        #print( "Limiting to single-threading on Windows (until we solve some bugs)" )
        #BibleOrgSysGlobals.maxProcesses = 1
    #print( 'MP', BibleOrgSysGlobals.maxProcesses )

    if 'win' in sys.platform or BibleOrgSysGlobals.debugFlag:
        # Why don't these show in Windows until the program closes?
        #   Ah, coz of TextIOWrapper above.
        print( exp("Platform is"), sys.platform ) # e.g., 'linux, or 'win32' for my Windows-10 (64-bit)
        print( exp("OS name is"), os.name ) # e.g., 'posix', or 'nt' for my Windows-10
        if sys.platform == 'linux': print( exp("OS uname is"), os.uname() ) # gives about five fields
        import locale
        print( "default locale", locale.getdefaultlocale() ) # ('en_NZ', 'cp1252') for my Windows-10
        print( "preferredEncoding", locale.getpreferredencoding() ) # cp1252 for my Windows-10
        print( exp("About to run main()…") )

    main( homeFolderPath, loggingFolderPath )

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of Biblelator.py
