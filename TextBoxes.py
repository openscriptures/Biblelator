#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TextBoxes.py
#
# Base of various textboxes for use as widgets and base classes in various windows.
#
# Copyright (C) 2013-2016 Robert Hunt
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
Base widgets to allow display and manipulation of
    various Bible and lexicon, etc. child windows.

class HTMLText( tk.Text )
    __init__( self, *args, **kwargs )
    insert( self, point, iText )
    _getURL( self, event )
    openHyperlink( self, event )
    overHyperlink( self, event )
    leaveHyperlink( self, event )

class CustomText( tk.Text )
    __init__( self, *args, **kwargs )
    setTextChangeCallback( self, callableFunction )

class ChildBox
    __init__( self, parentApp )
    _createStandardKeyboardBinding( self, name, command )
    createStandardKeyboardBindings( self )
    setFocus( self, event )
    doCopy( self, event=None )
    doSelectAll( self, event=None )
    doGotoWindowLine( self, event=None, forceline=None )
    doWindowFind( self, event=None, lastkey=None )
    doWindowRefind( self, event=None )
    doShowInfo( self, event=None )
    clearText( self ) # Leaves in normal state
    isEmpty( self )
    modified( self )
    getAllText( self )
    setAllText( self, newText )
    doShowMainWindow( self, event=None )
    doClose( self, event=None )

class BibleBox( ChildBox )
    displayAppendVerse( self, firstFlag, verseKey, verseContextData, lastFlag=True, currentVerse=False )
    getBeforeAndAfterBibleData( self, newVerseKey )

"""

from gettext import gettext as _

LastModifiedDate = '2016-08-11' # by RJH
ShortProgName = "TextBoxes"
ProgName = "Specialised text widgets"
ProgVersion = '0.38'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging

import tkinter as tk
from tkinter.simpledialog import askstring, askinteger

# Biblelator imports
from BiblelatorGlobals import APP_NAME, START, DEFAULT, errorBeep, \
                                BIBLE_FORMAT_VIEW_MODES

# BibleOrgSys imports
if __name__ == '__main__': import sys; sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals
from InternalBibleInternals import InternalBibleEntry
from VerseReferences import SimpleVerseKey
from BibleStylesheets import DEFAULT_FONTNAME



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
    return '{}{}'.format( nameBit, errorBit )
# end of exp



KNOWN_HTML_TAGS = ('!DOCTYPE','html','head','meta','link','title','body','div',
                   'h1','h2','h3','p','li','a','span','table','tr','td','i','b','em','small')
NON_FORMATTING_TAGS = 'html','head','body','div','table','tr','td', # Not sure about div yet...........
HTML_REPLACEMENTS = ('&nbsp;',' '),('&lt;','<'),('&gt;','>'),('&amp;','&'),
TRAILING_SPACE_SUBSTITUTE = '⦻' # Must not normally occur in Bible text
MULTIPLE_SPACE_SUBSTITUTE = '⧦' # Must not normally occur in Bible text
DOUBLE_SPACE_SUBSTITUTE = MULTIPLE_SPACE_SUBSTITUTE + MULTIPLE_SPACE_SUBSTITUTE
CLEANUP_LAST_MULTIPLE_SPACE = MULTIPLE_SPACE_SUBSTITUTE + ' '
TRAILING_SPACE_LINE = ' \n'
TRAILING_SPACE_LINE_SUBSTITUTE = TRAILING_SPACE_SUBSTITUTE + '\n'
ALL_POSSIBLE_SPACE_CHARS = ' ' + TRAILING_SPACE_SUBSTITUTE + MULTIPLE_SPACE_SUBSTITUTE



class HTMLText( tk.Text ):
    """
    A custom Text widget which understands and displays simple HTML.

    It currently accepts:
        heading tags:           h1,h2,h3
        paragraph tags:         p, li
        formatting tags:        span
        hard-formatting tags:   i, b, em

    For the styling, class names are appended to the tag names following a hyphen,
        e.g., <span class="Word"> would give an internal style of "spanWord".
    """
    def __init__( self, *args, **kwargs ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("HTMLText.__init__( {}, {} )").format( args, kwargs ) )
        tk.Text.__init__( self, *args, **kwargs ) # initialise the base class

        standardFont = DEFAULT_FONTNAME + ' 12'
        smallFont = DEFAULT_FONTNAME + ' 10'
        self.styleDict = { # earliest entries have the highest priority
            'i': { 'font':standardFont+' italic' },
            'b': { 'font':standardFont+' bold' },
            'em': { 'font':standardFont+' bold' },
            'p_i': { 'font':standardFont+' italic' },
            'p_b': { 'font':standardFont+' bold' },
            'p_em': { 'font':standardFont+' bold' },

            'span': { 'foreground':'red', 'font':standardFont },
            'li': { 'lmargin1':4, 'lmargin2':4, 'background':'pink', 'font':standardFont },
            'a': { 'foreground':'blue', 'font':standardFont, 'underline':1 },

            'small_p': { 'background':'pink', 'font':smallFont, 'spacing1':'1' },
            'small_p_pGeneratedNotice': { 'justify':tk.CENTER, 'background':'green', 'font':smallFont, 'spacing1':'1' },

            'small_p_a': { 'foreground':'blue', 'font':smallFont, 'underline':1, 'spacing1':'1' },
            'small_p_b': { 'background':'pink', 'font':smallFont+' bold', 'spacing1':'1' },

            'p': { 'background':'pink', 'font':standardFont, 'spacing1':'1' },
            'pGeneratedNotice': { 'justify':tk.CENTER, 'background':'green', 'font':smallFont, 'spacing1':'1' },

            'p_a': { 'foreground':'blue', 'font':standardFont, 'underline':1, 'spacing1':'1' },
            'p_span': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanGreekWord': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanHebrewWord': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanKJVUsage': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanStatus': { 'foreground':'red', 'background':'pink', 'font':standardFont },

            'p_spanSource': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanSource_b': { 'foreground':'red', 'background':'pink', 'font':standardFont+' bold' },
            'p_spanSource_span': { 'foreground':'red', 'background':'pink', 'font':standardFont, 'spacing1':'1' },
            'p_spanSource_spanDef': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanSource_spanHebrew': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanSource_spanStrongs': { 'foreground':'red', 'background':'pink', 'font':standardFont },

            'p_spanMeaning': { 'foreground':'red', 'background':'pink', 'font':standardFont },
            'p_spanMeaning_b': { 'foreground':'red', 'background':'pink', 'font':standardFont+' bold' },
            'p_spanMeaning_spanDef': { 'foreground':'red', 'background':'pink', 'font':standardFont },

            'p_span_b': { 'foreground':'red', 'background':'pink', 'font':standardFont+' bold' },
            'p_spanKJVUsage_b': { 'foreground':'red', 'background':'pink', 'font':standardFont+' bold' },

            #'td_a': { 'foreground':'blue', 'font':standardFont, 'underline':1 },
            #'h1_td_a': { 'foreground':'blue', 'font':standardFont, 'underline':1 },

            'h1': { 'justify':tk.CENTER, 'foreground':'blue', 'font':DEFAULT_FONTNAME+' 15', 'spacing1':'1', 'spacing3':'0.5' },
            'h1_a': { 'justify':tk.CENTER, 'foreground':'blue', 'font':DEFAULT_FONTNAME+' 15', 'spacing1':'1', 'spacing3':'0.5',  'underline':1 },
            'h1PageHeading': { 'justify':tk.CENTER, 'foreground':'blue', 'font':DEFAULT_FONTNAME+' 15', 'spacing1':'1', 'spacing3':'0.5' },
            'h2': { 'justify':tk.CENTER, 'foreground':'green', 'font':DEFAULT_FONTNAME+' 14', 'spacing1':'0.8', 'spacing3':'0.3' },
            'h3': { 'justify':tk.CENTER, 'foreground':'orange', 'font':DEFAULT_FONTNAME+' 13', 'spacing1':'0.5', 'spacing3':'0.2' },
            }
        for tag,styleEntry in self.styleDict.items():
            self.tag_configure( tag, **styleEntry ) # Create the style
        #background='yellow', font='helvetica 14 bold', relief=tk.RAISED
        #"background", "bgstipple", "borderwidth", "elide", "fgstipple",
        #"font", "foreground", "justify", "lmargin1", "lmargin2", "offset",
        #"overstrike", "relief", "rmargin", "spacing1", "spacing2", "spacing3",
        #"tabs", "tabstyle", "underline", and "wrap".

        aTags = ('a','p_a','small_p_a','h1_a')
        for tag in self.styleDict:
            if tag.endswith( '_a' ): assert tag in aTags
        for tag in aTags:
            assert tag in self.styleDict
            self.tag_bind( tag, '<Button-1>', self.openHyperlink )
            #self.tag_bind( tag, '<Enter>', self.overHyperlink )
            #self.tag_bind( tag, '<Leave>', self.leaveHyperlink )

        self._lastOverLink = None
    # end of HTMLText.__init__


    def insert( self, point, iText ):
        """
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("HTMLText.insert( {}, {} )").format( repr(point), repr(iText) ) )

        if point != tk.END:
            logging.critical( exp("HTMLText.insert doesn't know how to insert at {}").format( repr(point) ) )
            tk.Text.insert( self, point, iText )
            return

        # Fix whitespace in our text to how we want it
        remainingText = iText.replace( '\n', ' ' )
        remainingText = remainingText.replace( '<br>','\n' ).replace( '<br />','\n' ).replace( '<br/>','\n' )
        while '  ' in remainingText: remainingText = remainingText.replace( '  ', ' ' )

        currentFormatTags, currentHTMLTags = [], []
        #first = True
        while remainingText:
            #try: print( "  Remaining: {}".format( repr(remainingText) ) )
            #except UnicodeEncodeError: print( "  Remaining: {}".format( len(remainingText) ) )
            ix = remainingText.find( '<' )
            if ix == -1: # none found
                tk.Text.insert( self, point, remainingText, currentFormatTags ) # just insert all the remainingText
                remainingText = ""
            else: # presumably we have found the start of a new HTML tag
                if ix > 0: # this is where text is actually inserted into the box
                    insertText = remainingText[:ix]
                    if HTMLTag and HTMLTag == 'title':
                        pass # This is handled elsewhere
                    elif insertText: # it's not a title and not blank so we need to display this text
                        # Combine tag formats (but ignore consecutive identical tags e.g., p with a p
                        combinedFormats, lastTag, link = '', None, None
                        #print( "cFT", currentFormatTags )
                        for tag in currentFormatTags:
                            if tag.startswith( 'a=' ):
                                tag, link = 'a', tag[2:]
                                #print( "Got <a> link {}".format( repr(link) ) )
                            if tag != lastTag:
                                if combinedFormats: combinedFormats += '_'
                                combinedFormats += tag
                                lastTag = tag
                        #print( "combinedFormats", repr(combinedFormats) )
                        if combinedFormats and combinedFormats not in self.styleDict:
                            print( "  Missing format:", repr(combinedFormats), "cFT", currentFormatTags, "cHT", currentHTMLTags )
                            #try: print( "   on", repr(remainingText[:ix]) )
                            #except UnicodeEncodeError: pass
                        insertText = remainingText[:ix]
                        #print( "  Got format:", repr(combinedFormats), "cFT", currentFormatTags, "cHT", currentHTMLTags, repr(insertText) )
                        if 'Hebrew' in combinedFormats:
                            #print( "Reversing", repr(insertText ) )
                            insertText = insertText[::-1] # Reverse the string (a horrible way to approximate RTL)
                        for htmlChars, replacementChars in HTML_REPLACEMENTS:
                            insertText = insertText.replace( htmlChars, replacementChars )
                        #if link: print( "insertMarks", repr( (combinedFormats, 'href'+link,) if link else combinedFormats ) )
                        if link:
                            hypertag = 'href' + link
                            tk.Text.insert( self, point, insertText, (combinedFormats, hypertag,) )
                            self.tag_bind( hypertag, '<Enter>', self.overHyperlink )
                            self.tag_bind( hypertag, '<Leave>', self.leaveHyperlink )
                        else: tk.Text.insert( self, point, insertText, combinedFormats )
                        #first = False
                    remainingText = remainingText[ix:]
                #try: print( "  tag", repr(remainingText[:5]) )
                #except UnicodeEncodeError: print( "  tag" )
                ixEnd = remainingText.find( '>' )
                ixNext = remainingText.find( '<', 1 )
                #print( "ixEnd", ixEnd, "ixNext", ixNext )
                if ixEnd == -1 \
                or (ixEnd!=-1 and ixNext!=-1 and ixEnd>ixNext): # no tag close or wrong tag closed
                    logging.critical( exp("HTMLText.insert: Missing close bracket") )
                    tk.Text.insert( self, point, remainingText, currentFormatTags )
                    remainingText = ""
                    break
                # There's a close marker -- check it's our one
                fullHTMLTag = remainingText[1:ixEnd] # but without the < >
                remainingText = remainingText[ixEnd+1:]
                #if remainingText:
                    #try: print( "after marker", remainingText[0] )
                    #except UnicodeEncodeError: pass
                if not fullHTMLTag:
                    logging.critical( exp("HTMLText.insert: Unexpected empty HTML tags") )
                    continue
                selfClosing = fullHTMLTag[-1] == '/'
                if selfClosing:
                    fullHTMLTag = fullHTMLTag[:-1]
                #try: print( "fullHTMLTag", repr(fullHTMLTag), "self-closing" if selfClosing else "" )
                #except UnicodeEncodeError: pass

                # Can't do a normal split coz can have a space within a link, e.g., href="one two.htm"
                fullHTMLTagBits = []
                insideDoubleQuotes = False
                currentField = ""
                for char in fullHTMLTag:
                    if char in (' ',) and not insideDoubleQuotes:
                        fullHTMLTagBits.append( currentField )
                        currentField = ""
                    else:
                        currentField += char
                        if char == '"': insideDoubleQuotes = not insideDoubleQuotes
                if currentField: fullHTMLTagBits.append( currentField ) # Make sure we get the last bit
                #print( "{} got {}".format( repr(fullHTMLTag), fullHTMLTagBits ) )
                HTMLTag = fullHTMLTagBits[0]
                #print( "HTMLTag", repr(HTMLTag) )

                if HTMLTag and HTMLTag[0] == '/': # it's a close tag
                    assert len(fullHTMLTagBits) == 1 # shouldn't have any attributes on a closing tag
                    assert not selfClosing
                    HTMLTag = HTMLTag[1:]
                    #print( exp("Got HTML {} close tag").format( repr(HTMLTag) ) )
                    #print( "cHT1", currentHTMLTags )
                    #print( "cFT1", currentFormatTags )
                    if currentHTMLTags and HTMLTag == currentHTMLTags[-1]: # all good
                        currentHTMLTags.pop() # Drop it
                        if HTMLTag not in NON_FORMATTING_TAGS:
                            currentFormatTags.pop()
                    elif currentHTMLTags:
                        logging.critical( exp("HTMLText.insert: Expected to close {} but got {} instead").format( repr(currentHTMLTags[-1]), repr(HTMLTag) ) )
                    else:
                        logging.critical( exp("HTMLText.insert: Unexpected HTML close {} close marker").format( repr(HTMLTag) ) )
                    #print( "cHT2", currentHTMLTags )
                    #print( "cFT2", currentFormatTags )
                else: # it's not a close tag so must be an open tag
                    if HTMLTag not in KNOWN_HTML_TAGS:
                        logging.critical( exp("HTMLText doesn't recognise or handle {} as an HTML tag").format( repr(HTMLTag) ) )
                        #currentHTMLTags.append( HTMLTag ) # remember it anyway in case it's closed later
                        continue
                    if HTMLTag in ('h1','h2','h3','p','li','table','tr',):
                        tk.Text.insert( self, point, '\n' )
                    #elif HTMLTag in ('li',):
                        #tk.Text.insert( self, point, '\n' )
                    elif HTMLTag in ('td',):
                        tk.Text.insert( self, point, '\t' )
                    formatTag = HTMLTag
                    if len(fullHTMLTagBits)>1: # our HTML tag has some additional attributes
                        #print( "Looking for attributes" )
                        for bit in fullHTMLTagBits[1:]:
                            #try: print( "  bit", repr(bit) )
                            #except UnicodeEncodeError: pass
                            if bit.startswith('class="') and bit[-1]=='"':
                                formatTag += bit[7:-1] # create a tag like 'spanWord' or 'pVerse'
                            elif formatTag=='a' and bit.startswith('href="') and bit[-1]=='"':
                                formatTag += '=' + bit[6:-1] # create a tag like 'a=http://something.com'
                            else: logging.critical( "Ignoring {} attribute on {} tag".format( bit, repr(HTMLTag) ) )
                    if not selfClosing:
                        if HTMLTag != '!DOCTYPE':
                            currentHTMLTags.append( HTMLTag )
                            if HTMLTag not in NON_FORMATTING_TAGS:
                                currentFormatTags.append( formatTag )
        if currentHTMLTags:
            logging.critical( exp("HTMLText.insert: Left-over HTML tags: {}").format( currentHTMLTags ) )
        if currentFormatTags:
            logging.critical( exp("HTMLText.insert: Left-over format tags: {}").format( currentFormatTags ) )
    # end of HTMLText.insert


    def _getURL( self, event ):
        """
        Give a mouse event, get the URL underneath it.
        """
        # get the index of the mouse cursor from the event.x and y attributes
        xy = '@{0},{1}'.format( event.x, event.y )
        #print( "xy", repr(xy) ) # e.g.., '@34,77'
        #print( "ixy", repr(self.index(xy)) ) # e.g., '4.3'

        #URL = None
        tagNames = self.tag_names( xy )
        #print( "tn", tagNames )
        for tagName in tagNames:
            if tagName.startswith( 'href' ):
                URL = tagName[4:]
                #print( "URL", repr(URL) )
                return URL
    # end of HTMLText._getURL


    def openHyperlink( self, event ):
        """
        Handle a click on a hyperlink.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("HTMLText.openHyperlink()") )
        URL = self._getURL( event )

        #if BibleOrgSysGlobals.debugFlag: # Find the range of the tag nearest the index
            #xy = '@{0},{1}'.format( event.x, event.y )
            #tagNames = self.tag_names( xy )
            #print( "tn", tagNames )
            #for tagName in tagNames:
                #if tagName.startswith( 'href' ): break
            #tag_range = self.tag_prevrange( tagName, xy )
            #print( "tr", repr(tag_range) ) # e.g., ('6.0', '6.13')
            #clickedText = self.get( *tag_range )
            #print( "Clicked on {}".format( repr(clickedText) ) )

        if URL: self.master.gotoLink( URL )
    # end of HTMLText.openHyperlink


    def overHyperlink( self, event ):
        """
        Handle a mouseover on a hyperlink.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("HTMLText.overHyperlink()") )
        URL = self._getURL( event )

        #if BibleOrgSysGlobals.debugFlag: # Find the range of the tag nearest the index
            #xy = '@{0},{1}'.format( event.x, event.y )
            #tagNames = self.tag_names( xy )
            #print( "tn", tagNames )
            #for tagName in tagNames:
                #if tagName.startswith( 'href' ): break
            #tag_range = self.tag_prevrange( tagName, xy )
            #print( "tr", repr(tag_range) ) # e.g., ('6.0', '6.13')
            #clickedText = self.get( *tag_range )
            #print( "Over {}".format( repr(clickedText) ) )

        if URL: self.master.overLink( URL )
    # end of HTMLText.overHyperlink

    def leaveHyperlink( self, event ):
        """
        Handle a mouseover on a hyperlink.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( exp("HTMLText.leaveHyperlink()") )
        self.master.leaveLink()
    # end of HTMLText.leaveHyperlink
# end of HTMLText class



class CustomText( tk.Text ):
    """
    A custom Text widget which calls a user function whenever the text changes.

    Adapted from http://stackoverflow.com/questions/13835207/binding-to-cursor-movement-doesnt-change-insert-mark

    Also contains a function to highlight specific patterns.
    """
    def __init__( self, *args, **kwargs ):
        """
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("CustomText.__init__( {}, {} )").format( args, kwargs ) )
        tk.Text.__init__( self, *args, **kwargs ) # initialise the base class

        # All widget changes happen via an internal Tcl command with the same name as the widget:
        #       all inserts, deletes, cursor changes, etc
        #
        # The beauty of Tcl is that we can replace that command with our own command.
        # The following code does just that: replace the code with a proxy that calls the
        # original command and then calls a callback. We can then do whatever we want in the callback.
        private_callback = self.register( self._callback )
        self.tk.eval( """
            proc widget_proxy {actual_widget callback args} {

                # this prevents recursion if the widget is called
                # during the callback
                set flag ::dont_recurse(actual_widget)

                # call the real tk widget with the real args
                set result [uplevel [linsert $args 0 $actual_widget]]

                # call the callback and ignore errors, but only
                # do so on inserts, deletes, and changes in the
                # mark. Otherwise we'll call the callback way too often.
                if {! [info exists $flag]} {
                    if {([lindex $args 0] in {insert replace delete}) ||
                        ([lrange $args 0 2] == {mark set insert})} {
                        # the flag makes sure that whatever happens in the
                        # callback doesn't cause the callbacks to be called again.
                        set $flag 1
                        catch {$callback $result {*}$args } callback_result
                        unset -nocomplain $flag
                    }
                }

                # return the result from the real widget command
                return $result
            }
            """ )
        self.tk.eval( """
                rename {widget} _{widget}
                interp alias {{}} ::{widget} {{}} widget_proxy _{widget} {callback}
            """.format( widget=str(self), callback=private_callback ) )
    # end of CustomText.__init__


    def _callback( self, result, *args ):
        """
        This little function does the actual call of the user routine
            to handle when the CustomText changes.
        """
        self.callbackFunction( result, *args )
    # end of CustomText._callback


    def setTextChangeCallback( self, callableFunction ):
        """
        Just a little function to remember the routine to call
            when the CustomText changes.
        """
        self.callbackFunction = callableFunction
    # end of CustomText.setTextChangeCallback


    def highlightPattern( self, pattern, styleTag, startAt=START, endAt=tk.END, regexpFlag=True ):
        """
        Apply the given tag to all text that matches the given pattern.

        Useful for syntax highlighting, etc.

        # Adapted from http://stackoverflow.com/questions/4028446/python-tkinter-help-menu
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "CustomText.highlightPattern( {}, {}, start={}, end={}, regexp={} )".format( pattern, styleTag, startAt, endAt, regexpFlag ) )

        countVar = tk.IntVar()
        matchEnd = startAt
        while True:
            #print( "here0 mS={!r} mE={!r} sL={!r}".format( self.index("matchStart"), self.index("matchEnd"), self.index("searchLimit") ) )
            index = self.search( pattern, matchEnd, stopindex=endAt, count=countVar, regexp=regexpFlag )
            #print( "here1", repr(index), repr(countVar.get()) )
            if index == "": break
            #print( "here2", self.index("matchStart"), self.index("matchEnd") )
            matchEnd = "{}+{}c".format( index, countVar.get() )
            self.tag_add( styleTag, index, matchEnd )
    # end of CustomText.highlightPattern


    def highlightAllPatterns( self, patternCollection ):
        """
        Given a collection of 4-tuples, apply the styles to the patterns in the text.

        Each tuple is:
            regexpFlag: True/False
            pattern to search for
            tagName
            tagDict, e.g, {"background":"red"}
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("CustomText.highlightAllPatterns( {} )").format( patternCollection ) )

        for regexpFlag, pattern, tagName, tagDict in patternCollection:
            self.tag_configure( tagName, **tagDict )
            self.highlightPattern( pattern, tagName, regexpFlag=regexpFlag )
    # end of CustomText.highlightAllPatterns
# end of CustomText class



class ChildBox():
    """
    A set of functions that work for any frame or window that has a member: self.textBox
    """
    def __init__( self, parentApp ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.__init__( {} )").format( parentApp ) )
            assert parentApp
        self.parentApp = parentApp

        self.myKeyboardBindingsList = []
        if BibleOrgSysGlobals.debugFlag: self.myKeyboardShortcutsList = [] # Just for catching setting of duplicates

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.__init__ finished.") )
    # end of ChildBox.__init__


    def _createStandardKeyboardBinding( self, name, command ):
        """
        Called from createStandardKeyboardBindings to do the actual work.
        """
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("ChildBox._createStandardKeyboardBinding( {} )").format( name ) )

        try: kBD = self.parentApp.keyBindingDict
        except AttributeError: kBD = self.parentWindow.parentApp.keyBindingDict
        assert (name,kBD[name][0],) not in self.myKeyboardBindingsList
        if name in kBD:
            for keyCode in kBD[name][1:]:
                #print( "Bind {} for {}".format( repr(keyCode), repr(name) ) )
                self.textBox.bind( keyCode, command )
                if BibleOrgSysGlobals.debugFlag:
                    assert keyCode not in self.myKeyboardShortcutsList
                    self.myKeyboardShortcutsList.append( keyCode )
            self.myKeyboardBindingsList.append( (name,kBD[name][0],) )
        else: logging.critical( 'No key binding available for {}'.format( repr(name) ) )
    # end of ChildBox._createStandardKeyboardBinding()

    def createStandardKeyboardBindings( self ):
        """
        Create keyboard bindings for this widget.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.createStandardKeyboardBindings()") )

        for name,command in ( ('SelectAll',self.doSelectAll), ('Copy',self.doCopy),
                             ('Find',self.doWindowFind), ('Refind',self.doWindowRefind),
                             ('Help',self.doHelp), ('Info',self.doShowInfo), ('About',self.doAbout),
                             ('Close',self.doClose), ('ShowMain',self.doShowMainWindow), ):
            self._createStandardKeyboardBinding( name, command )
    # end of ChildBox.createStandardKeyboardBindings()


    def setFocus( self, event ):
        '''Explicitly set focus, so user can select and copy text'''
        self.textBox.focus_set()


    def doCopy( self, event=None ):
        """
        Copy the selected text onto the clipboard.
        """
        from BiblelatorDialogs import showerror
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doCopy( {} )").format( event ) )

        if not self.textBox.tag_ranges( tk.SEL ):       # save in cross-app clipboard
            errorBeep()
            showerror( self, APP_NAME, _("No text selected") )
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
            print( exp("ChildBox.doSelectAll( {} )").format( event ) )

        self.textBox.tag_add( tk.SEL, START, tk.END+'-1c' )   # select entire text
        self.textBox.mark_set( tk.INSERT, START )          # move insert point to top
        self.textBox.see( tk.INSERT )                      # scroll to top
    # end of ChildBox.doSelectAll


    def doGotoWindowLine( self, event=None, forceline=None ):
        """
        """
        from BiblelatorDialogs import showerror
        self.parentApp.logUsage( ProgName, debuggingThisModule, 'ChildBox doGotoWindowLine {}'.format( forceline ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doGotoWindowLine( {}, {} )").format( event, forceline ) )

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
    # end of ChildBox.doGotoWindowLine


    def doWindowFind( self, event=None, lastkey=None ):
        """
        """
        from BiblelatorDialogs import showerror
        self.parentApp.logUsage( ProgName, debuggingThisModule, 'ChildBox doWindowFind {!r}'.format( lastkey ) )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doWindowFind( {}, {!r} )").format( event, lastkey ) )

        key = lastkey or askstring( APP_NAME, _("Enter search string") )
        self.textBox.update()
        self.textBox.focus()
        self.lastfind = key
        if key:
            nocase = self.optionsDict['caseinsens']
            where = self.textBox.search( key, tk.INSERT, tk.END, nocase=nocase )
            if not where:                                          # don't wrap
                errorBeep()
                showerror( self, APP_NAME, _("String {!r} not found").format( key if len(key)<20 else (key[:18]+'…') ) )
            else:
                pastkey = where + '+%dc' % len(key)           # index past key
                self.textBox.tag_remove( tk.SEL, START, tk.END )         # remove any sel
                self.textBox.tag_add( tk.SEL, where, pastkey )        # select key
                self.textBox.mark_set( tk.INSERT, pastkey )           # for next find
                self.textBox.see( where )                          # scroll display
    # end of ChildBox.doWindowFind


    def doWindowRefind( self, event=None ):
        """
        """
        self.parentApp.logUsage( ProgName, debuggingThisModule, 'ChildBox doWindowRefind' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doWindowRefind( {} ) for {!r}").format( event, self.lastfind ) )

        self.doWindowFind( lastkey=self.lastfind )
    # end of ChildBox.doWindowRefind


    def doShowInfo( self, event=None ):
        """
        Pop-up dialog giving text statistics and cursor location;
        caveat (2.1): Tk insert position column counts a tab as one
        character: translate to next multiple of 8 to match visual?
        """
        from BiblelatorDialogs import showinfo
        self.parentApp.logUsage( ProgName, debuggingThisModule, 'ChildBox doShowInfo' )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doShowInfo( {} )").format( event ) )

        text  = self.getAllText()
        numChars = len( text )
        numLines = len( text.split('\n') )
        numWords = len( text.split() )
        index = self.textBox.index( tk.INSERT )
        atLine, atColumn = index.split('.')
        infoString = 'Current location:\n' \
                 + '  Line:\t{}\n  Column:\t{}\n'.format( atLine, atColumn ) \
                 + '\nFile text statistics:\n' \
                 + '  Chars:\t{}\n  Lines:\t{}\n  Words:\t{}'.format( numChars, numLines, numWords )
        showinfo( self, 'Window Information', infoString )
    # end of ChildBox.doShowInfo


    ############################################################################
    # Utilities, useful outside this class
    ############################################################################

    def clearText( self ): # Leaves in normal state
        self.textBox.config( state=tk.NORMAL )
        self.textBox.delete( START, tk.END )
    # end of ChildBox.updateText


    def isEmpty( self ):
        return not self.getAllText()
    # end of ChildBox.isEmpty


    def modified( self ):
        return self.textBox.edit_modified()
    # end of ChildBox.modified


    def getAllText( self ):
        """
        Returns all the text as a string.
        """
        return self.textBox.get( START, tk.END+'-1c' )
    # end of ChildBox.getAllText


    def setAllText( self, newText ):
        """
        Sets the textBox (assumed to be enabled) to the given text
            then positions the insert cursor at the BEGINNING of the text.

        caller: call self.update() first if just packed, else the
        initial position may be at line 2, not line 1 (2.1; Tk bug?)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.setAllText( {!r} )").format( newText ) )

        self.textBox.config( state=tk.NORMAL ) # In case it was disabled
        self.textBox.delete( START, tk.END ) # Delete everything that's existing
        self.textBox.insert( tk.END, newText )
        self.textBox.mark_set( tk.INSERT, START ) # move insert point to top
        self.textBox.see( tk.INSERT ) # scroll to top, insert is set

        self.textBox.edit_reset() # clear undo/redo stks
        self.textBox.edit_modified( tk.FALSE ) # clear modified flag
    # end of ChildBox.setAllText


    def doShowMainWindow( self, event=None ):
        """
        Display the main window (it might be minimised or covered).
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doShowMainWindow( {} )").format( event ) )

        #self.parentApp.rootWindow.iconify() # Didn't help
        self.parentApp.rootWindow.withdraw() # For some reason, doing this first makes the window always appear above others
        self.parentApp.rootWindow.update()
        self.parentApp.rootWindow.deiconify()
        #self.parentApp.rootWindow.focus_set()
        self.parentApp.rootWindow.lift() # aboveThis=self )
    # end of ChildBox.doShowMainWindow


    def doClose( self, event=None ):
        """
        Called from the GUI.

        Can be overridden if an edit box needs to save files first.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("ChildBox.doClose( {} )").format( event ) )

        self.destroy()
    # end of ChildBox.doClose
# end of ChildBox class



class BibleBox( ChildBox ):
    """
    A set of functions that work for any Bible frame or window that has a member: self.textBox
        and also uses verseKeys
    """
    def displayAppendVerse( self, firstFlag, verseKey, verseContextData, lastFlag=True, currentVerse=False, substituteTrailingSpaces=False, substituteMultipleSpaces=False ):
        """
        Add the requested verse to the end of self.textBox.

        It connects the USFM markers as stylenames while it's doing it
            and adds the CV marks at the same time for navigation.

        Usually called from updateShownBCV from the subclass.
        Note that it's used in both formatted and unformatted (even edit) windows.
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule:
                print( "displayAppendVerse( {}, {}, {}, {}, {}, {}, {} )".format( firstFlag, verseKey, verseContextData, lastFlag, currentVerse, substituteTrailingSpaces, substituteMultipleSpaces ) )
            assert isinstance( firstFlag, bool )
            assert isinstance( verseKey, SimpleVerseKey )
            if verseContextData:
                assert isinstance( verseContextData, tuple ) and len(verseContextData)==2 or isinstance( verseContextData, str )
            assert isinstance( lastFlag, bool )
            assert isinstance( currentVerse, bool )

        def insertEnd( ieText, ieTags ):
            """
            Insert the formatted text into the end of the textbox.

            The function mostly exists so we can print the parameters if necessary for debugging.
            """
            if BibleOrgSysGlobals.debugFlag:
                if debuggingThisModule:
                    print( "insertEnd( {!r}, {} )".format( ieText, ieTags ) )
                assert isinstance( ieText, str )
                assert isinstance( ieTags, (str,tuple) )
                assert TRAILING_SPACE_SUBSTITUTE not in ieText
                assert MULTIPLE_SPACE_SUBSTITUTE not in ieText

            # Make any requested substitutions
            if substituteMultipleSpaces:
                ieText = ieText.replace( '  ', DOUBLE_SPACE_SUBSTITUTE )
                ieText = ieText.replace( CLEANUP_LAST_MULTIPLE_SPACE, DOUBLE_SPACE_SUBSTITUTE )
            if substituteTrailingSpaces:
                ieText = ieText.replace( TRAILING_SPACE_LINE, TRAILING_SPACE_LINE_SUBSTITUTE )

            self.textBox.insert( tk.END, ieText, ieTags )
        # end of BibleBox.displayAppendVerse.insertEnd


        # Start of main code for BibleBox.displayAppendVerse
        try: cVM, fVM = self._contextViewMode, self._formatViewMode
        except AttributeError: # Must be called from a box, not a window so get settings from parent
            cVM, fVM = self.parentWindow._contextViewMode, self.parentWindow._formatViewMode
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("displayAppendVerse2( {}, {}, …, {}, {} ) for {}/{}").format( firstFlag, verseKey, lastFlag, currentVerse, fVM, cVM ) )

        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #print( exp("BibleBox.displayAppendVerse( {}, {}, …, {}, {} ) for {}/{}").format( firstFlag, verseKey, lastFlag, currentVerse, fVM, cVM ) )
            ##try: print( exp("BibleBox.displayAppendVerse( {}, {}, {}, {} )").format( firstFlag, verseKey, verseContextData, currentVerse ) )
            ##except UnicodeEncodeError: print( exp("BibleBox.displayAppendVerse"), firstFlag, verseKey, currentVerse )

        BBB, C, V = verseKey.getBCV()
        C, V = int(C), int(V)
        #C1 = C2 = int(C); V1 = V2 = int(V)
        #if V1 > 0: V1 -= 1
        #elif C1 > 0:
            #C1 -= 1
            #V1 = self.getNumVerses( BBB, C1 )
        #if V2 < self.getNumVerses( BBB, C2 ): V2 += 1
        #elif C2 < self.getNumChapters( BBB):
            #C2 += 1
            #V2 = 0
        #previousMarkName = 'C{}V{}'.format( C1, V1 )
        currentMarkName = 'C{}V{}'.format( C, V )
        #nextMarkName = 'C{}V{}'.format( C2, V2 )
        #print( "Marks", previousMarkName, currentMarkName, nextMarkName )

        lastCharWasSpace = haveTextFlag = not firstFlag

        if verseContextData is None:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and C!=0 and V!=0:
                print( "  ", exp("displayAppendVerse"), "has no data for", verseKey )
            verseDataList = context = None
        elif isinstance( verseContextData, tuple ):
            assert len(verseContextData) == 2
            verseDataList, context = verseContextData
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( "   VerseDataList: {}".format( verseDataList ) )
                #print( "   Context: {}".format( context ) )
        elif isinstance( verseContextData, str ):
            verseDataList, context = verseContextData.split( '\n' ), None
        elif BibleOrgSysGlobals.debugFlag: halt

        # Display the context preceding the first verse
        if firstFlag and context:
            #print( "context", context )
            #print( "  Setting context mark to {}".format( previousMarkName ) )
            #self.textBox.mark_set( previousMarkName, tk.INSERT )
            #self.textBox.mark_gravity( previousMarkName, tk.LEFT )
            insertEnd( "Context:", 'contextHeader' )
            contextString, firstMarker = "", True
            for someMarker in context:
                #print( "  someMarker", someMarker )
                if someMarker != 'chapters':
                    contextString += (' ' if firstMarker else ', ') + someMarker
                    firstMarker = False
            insertEnd( contextString, 'context' )
            haveTextFlag = True

        #print( "  Setting mark to {}".format( currentMarkName ) )
        self.textBox.mark_set( currentMarkName, tk.INSERT )
        self.textBox.mark_gravity( currentMarkName, tk.LEFT )

        if verseDataList is None:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and C!=0 and V!=0:
                print( "  ", exp("BibleBox.displayAppendVerse"), "has no data for", self.moduleID, verseKey )
            #self.textBox.insert( tk.END, '--' )
        else:
            #hadVerseText = False
            #try: cVM = self._contextViewMode
            #except AttributeError: cVM = self.parentWindow._contextViewMode
            lastParagraphMarker = context[-1] if context and context[-1] in BibleOrgSysGlobals.USFMParagraphMarkers \
                                        else 'v~' # If we don't know the format of a verse (or for unformatted Bibles)
            endMarkers = []

            for entry in verseDataList:
                # This loop is used for several types of data
                if isinstance( entry, InternalBibleEntry ):
                    marker, cleanText = entry.getMarker(), entry.getCleanText()
                elif isinstance( entry, tuple ):
                    marker, cleanText = entry[0], entry[3]
                elif isinstance( entry, str ): # from a Bible text editor window
                    if entry=='': continue
                    entry += '\n'
                    if entry[0]=='\\':
                        marker = ''
                        for char in entry[1:]:
                            if char!='¬' and not char.isalnum(): break
                            marker += char
                        cleanText = entry[len(marker)+1:].lstrip()
                    else:
                        marker, cleanText = None, entry
                elif BibleOrgSysGlobals.debugFlag: halt
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "  displayAppendVerse", lastParagraphMarker, haveTextFlag, marker, repr(cleanText) )

                if fVM == 'Unformatted':
                    if marker and marker[0]=='¬': pass # Ignore end markers for now
                    elif marker in ('intro','chapters','list',): pass # Ignore added markers for now
                    else:
                        if isinstance( entry, str ): # from a Bible text editor window
                            #print( "marker={!r}, entry={!r}".format( marker, entry ) )
                            insertEnd( entry, marker ) # Do it just as is!
                        else: # not a str, i.e., not a text editor, but a viewable resource
                            #if hadVerseText and marker in ( 's', 's1', 's2', 's3' ):
                                #print( "  Setting s mark to {}".format( nextMarkName ) )
                                #self.textBox.mark_set( nextMarkName, tk.INSERT )
                                #self.textBox.mark_gravity( nextMarkName, tk.LEFT )
                            #print( "  Inserting ({}): {!r}".format( marker, entry ) )
                            if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                            if marker is None:
                                insertEnd( cleanText, '###' )
                            else: insertEnd( '\\{} {}'.format( marker, cleanText ), marker+'#' )
                            haveTextFlag = True

                elif fVM == 'Formatted':
                    if marker.startswith( '¬' ):
                        if marker != '¬v': endMarkers.append( marker ) # Don't want end-verse markers
                    else: endMarkers = [] # Reset when we have normal markers

                    if marker.startswith( '¬' ):
                        pass # Ignore end markers for now
                        #assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        #if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        #insertEnd( cleanText, marker )
                        #haveTextFlag = True
                    elif marker == 'id':
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('ide','rem',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('h','toc1','toc2','toc3','cl¤',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('intro','chapters','list',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4', 'iot','io1','io2','io3','io4',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('ip','ipi','im','imi','ipq','imq','ipr', 'iq1','iq2','iq3','iq4',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('s1','s2','s3','s4', 'is1','is2','is3','is4', 'ms1','ms2','ms3','ms4', 'cl',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('d','sp',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in ('r','mr','sr',):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        insertEnd( cleanText, marker )
                        haveTextFlag = True
                    elif marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                        assert not cleanText # No text expected with these markers
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                        lastParagraphMarker = marker
                        haveTextFlag = True
                    elif marker in ('b','ib'):
                        assert marker not in BibleOrgSysGlobals.USFMParagraphMarkers
                        assert not cleanText # No text expected with this marker
                        if haveTextFlag: self.textBox.insert ( tk.END, '\n' )
                    #elif marker in ('m','im'):
                        #self.textBox.insert ( tk.END, '\n' if haveTextFlag else '  ', marker )
                        #if cleanText:
                            #insertEnd( cleanText, '*'+marker if currentVerse else marker )
                            #lastCharWasSpace = False
                            #haveTextFlag = True
                    elif marker == 'p#' and self.boxType=='DBPBibleResourceBox':
                        pass # Just ignore these for now
                    elif marker == 'c': # Don't want to display this (original) c marker
                        #if not firstFlag: haveC = cleanText
                        #else: print( "   Ignore C={}".format( cleanText ) )
                        pass
                    elif marker == 'c#': # Might want to display this (added) c marker
                        if cleanText != verseKey.getBBB():
                            if not lastCharWasSpace: insertEnd( ' ', 'v-' )
                            insertEnd( cleanText, (lastParagraphMarker,marker,) if lastParagraphMarker else (marker,) )
                            lastCharWasSpace = False
                    elif marker == 'v':
                        if cleanText != '1': # Don't display verse number for v1 in default view
                            if haveTextFlag:
                                insertEnd( ' ', (lastParagraphMarker,'v-',) if lastParagraphMarker else ('v-',) )
                            insertEnd( cleanText, (lastParagraphMarker,marker,) if lastParagraphMarker else (marker,) )
                            insertEnd( '\u2009', (lastParagraphMarker,'v+',) if lastParagraphMarker else ('v+',) ) # narrow space
                            lastCharWasSpace = haveTextFlag = True
                    elif marker in ('v~','p~'):
                        insertEnd( cleanText, '*'+lastParagraphMarker if currentVerse else lastParagraphMarker )
                        haveTextFlag = True
                    else:
                        if BibleOrgSysGlobals.debugFlag:
                            logging.critical( exp("BibleBox.displayAppendVerse (formatted): Unknown marker {!r} {!r} from {}").format( marker, cleanText, verseDataList ) )
                        else:
                            logging.critical( exp("BibleBox.displayAppendVerse (formatted): Unknown marker {!r} {!r}").format( marker, cleanText ) )
                else:
                    logging.critical( exp("BibleBox.displayAppendVerse: Unknown {!r} format view mode").format( fVM ) )
                    if BibleOrgSysGlobals.debugFlag: halt

            if lastFlag and cVM=='ByVerse' and endMarkers:
                #print( "endMarkers", endMarkers )
                insertEnd( " End context:", 'contextHeader' )
                contextString, firstMarker = "", True
                for someMarker in endMarkers:
                    #print( "  someMarker", someMarker )
                    contextString += (' ' if firstMarker else ', ') + someMarker
                    firstMarker = False
                insertEnd( contextString, 'context' )
    # end of BibleBox.displayAppendVerse


    def getBeforeAndAfterBibleData( self, newVerseKey ):
        """
        Returns the requested verse, the previous verse, and the next n verses.
        """
        if BibleOrgSysGlobals.debugFlag:
            print( exp("BibleBox.getBeforeAndAfterBibleData( {} )").format( newVerseKey ) )
            assert isinstance( newVerseKey, SimpleVerseKey )

        BBB, C, V = newVerseKey.getBCV()
        intC, intV = newVerseKey.getChapterNumberInt(), newVerseKey.getVerseNumberInt()

        # Determine the PREVIOUS valid verse numbers
        prevBBB, prevIntC, prevIntV = BBB, intC, intV
        previousVersesData = []
        for n in range( -self.parentApp.viewVersesBefore, 0 ):
            failed = False
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "  getBeforeAndAfterBibleData here with", n, prevIntC, prevIntV )
            if prevIntV > 0: prevIntV -= 1
            elif prevIntC > 0:
                prevIntC -= 1
                try: prevIntV = self.getNumVerses( prevBBB, prevIntC )
                except KeyError:
                    if prevIntC != 0: # we can expect an error for chapter zero
                        logging.error( exp("BibleBox.getBeforeAndAfterBibleData1 failed at {} {}").format( prevBBB, prevIntC ) )
                    failed = True
                #if not failed:
                    #if BibleOrgSysGlobals.debugFlag: print( " Went back to previous chapter", prevIntC, prevIntV, "from", BBB, C, V )
            else:
                try: prevBBB = self.BibleOrganisationalSystem.getPreviousBookCode( BBB )
                except KeyError: prevBBB = None
                if prevBBB is None: failed = True
                else:
                    prevIntC = self.getNumChapters( prevBBB )
                    prevIntV = self.getNumVerses( prevBBB, prevIntC )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( " Went back to previous book", prevBBB, prevIntC, prevIntV, "from", BBB, C, V )
                    if prevIntC is None or prevIntV is None:
                        logging.error( exp("BibleBox.getBeforeAndAfterBibleData2 failed at {} {}:{}").format( prevBBB, prevIntC, prevIntV ) )
                        #failed = True
                        break
            if not failed and prevIntV is not None:
                #print( "getBeforeAndAfterBibleData XXX", repr(prevBBB), repr(prevIntC), repr(prevIntV) )
                assert prevBBB and isinstance(prevBBB, str)
                previousVerseKey = SimpleVerseKey( prevBBB, prevIntC, prevIntV )
                previousVerseData = self.getCachedVerseData( previousVerseKey )
                if previousVerseData: previousVersesData.insert( 0, (previousVerseKey,previousVerseData,) ) # Put verses in backwards

        # Determine the NEXT valid verse numbers
        nextBBB, nextIntC, nextIntV = BBB, intC, intV
        nextVersesData = []
        for n in range( 0, self.parentApp.viewVersesAfter ):
            try: numVerses = self.getNumVerses( nextBBB, nextIntC )
            except KeyError: numVerses = None # for an invalid BBB
            nextIntV += 1
            if numVerses is None or nextIntV > numVerses:
                nextIntV = 1
                nextIntC += 1 # Need to check................................
            nextVerseKey = SimpleVerseKey( nextBBB, nextIntC, nextIntV )
            nextVerseData = self.getCachedVerseData( nextVerseKey )
            if nextVerseData: nextVersesData.append( (nextVerseKey,nextVerseData,) )

        # Get the CURRENT verse data
        verseData = self.getCachedVerseData( newVerseKey )

        return verseData, previousVersesData, nextVersesData
    # end of BibleBox.getBeforeAndAfterBibleData
# end of class BibleBox



def demo():
    """
    Demo program to handle command line parameters and then run what they want.
    """
    from tkinter import Tk

    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Available CPU count =", multiprocessing.cpu_count() )

    if BibleOrgSysGlobals.debugFlag: print( exp("Running demo…") )

    tkRootWindow = Tk()
    tkRootWindow.title( ProgNameVersionDate if BibleOrgSysGlobals.debugFlag else ProgNameVersion )

    HTMLTextbox = HTMLText( tkRootWindow )
    HTMLTextbox.pack()

    #application = Application( parent=tkRootWindow, settings=settings )
    # Calls to the window manager class (wm in Tk)
    #application.master.title( ProgNameVersion )
    #application.master.minsize( application.minimumXSize, application.minimumYSize )

    # Start the program running
    tkRootWindow.mainloop()
# end of TextBoxes.demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables


    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )


    if 1 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        from tkinter import TclVersion, TkVersion
        from tkinter import tix
        print( "TclVersion is", TclVersion )
        print( "TkVersion is", TkVersion )
        print( "tix TclVersion is", tix.TclVersion )
        print( "tix TkVersion is", tix.TkVersion )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of TextBoxes.py