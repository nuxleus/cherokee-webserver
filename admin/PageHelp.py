# -*- coding: utf-8 -*-
#
# Cherokee-admin
#
# Authors:
#      Taher Shihadeh <taher@unixwars.com>
#
# Copyright (C) 2010 Alvaro Lopez Ortega
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 2 of the GNU General Public
# License as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

import re
import os
import CTK
import Page
import configured

from CTK.consts import *

# Quitar html de la regla de cherokee
URL_BASE   = '/help'
TOC_TITLE  = N_('Table of Contents')

BODY_REGEX = """<div class="sectionbody">(.+?)</div>\s*<div id="footer">"""
LINK_REGEX = """<a href="(.+?)">(.+?)</a>""" #link, title

class Parser():
    """Simple documentation parser"""
    def __init__ (self, filename):
        self.filename = filename
        filepath  = os.path.join(configured.DOCDIR, filename)
        self.html = open(filepath).read()
        self.body = self.parse (BODY_REGEX, self.html)[0]
        self.sections = None

    def parse (self, regex, txt):
        return re.findall (regex, txt, re.DOTALL)

    def get_sections (self):
        if self.sections:
            return self.sections

        self.build_tree()
        self.sections = self.build_section (self.filename, _(TOC_TITLE))
        return self.sections

    def build_section (self, link, text):
        """
        entry = { 'link': link, 'text': title, 'children': [entry ...]}
        """
        entry = { 'link': link, 'text': text }
        children   = []
        childlinks = self.tree.get(link)
        if childlinks:
            for lnk,txt in self.links:
                if lnk in childlinks:
                    children.append (self.build_section (lnk, txt))
        entry['children'] = children
        return entry

    def build_tree (self):
        def branch_sorter (x, y):
            return len(y) - len(x)

        def is_covered (val):
            for key,vals in self.tree.items():
                if val in vals:
                    return True
            return False

        def tree_len ():
            tmp = []
            for vals in self.tree.values():
                tmp.extend(vals)
            return len(tmp)

        self.links = self.parse (LINK_REGEX, self.body)
        self.files = [x[0] for x in self.links]
        self.tree = {'index.html': [f for f in self.files if len(f.split('_'))==1]}
        delta     = 1

        while tree_len() < len(self.links):
            mess  = [(f, f.split('.html')[0].split('_')) for f in
                     self.files if not is_covered(f)]
            mess.sort (branch_sorter)
            self.build_helper (mess, delta)
            delta += 1

    def build_helper (self, mess, delta):
        for elem in mess:
            x = elem[1]
            name, idx = None, len(x)-delta
            if idx >= 0:
                name = '%s.html'%('_'.join(x[:idx]))
            if name in self.files:
                self.tree[name] = self.tree.get(name, [])
                childname = '%s.html'%('_'.join(x))
                self.tree[name].append(childname)


class IndexBox (CTK.Box):
    def __init__ (self, link, **kwargs):
        CTK.Box.__init__ (self, {'class': 'help_toc'}, **kwargs)
        parser        = Parser ('index.html')
        self.link     = link
        self.sections = parser.get_sections ()
        self         += self.process_entry (self.sections)

    def process_entry (self, entry):
        props = {}
        if entry['link'] == self.link:
            props['class'] = 'help_selected'
        block  = CTK.Table (props)
        block += [CTK.RawHTML(LINK_HREF%(entry['link'],entry['text']))]

        spawn = entry.get('children')
        if spawn:
            children = CTK.Container()
            for child in spawn:
                children += self.process_entry (child)
            block += [CTK.Indenter (children)]

        return block


class HelpBox (CTK.Box):
    def __init__ (self, filename, **kwargs):
        CTK.Box.__init__ (self, {'class': 'help_content'}, **kwargs)
        parser  = Parser (filename)
        self += CTK.RawHTML (parser.body)


class Render():
    def __call__ (self):
        # Content
        filename = CTK.request.url.split('/')[-1]
        left  = IndexBox(filename)
        right = HelpBox (filename)

        # Build the page
        page = Page ()
        page += left
        page += right

        return page.Render()

class Page (CTK.Page):
    def __init__ (self, **kwargs):
        # Look for the theme file
        srcdir = os.path.dirname (os.path.realpath (__file__))
        theme_file = os.path.join (srcdir, 'help.html')

        # Set up the template
        template = CTK.Template (filename = theme_file)

        template['title']      = _("Documentation")
        template['body_props'] = ' id="body-help"'

        # Parent's constructor
        CTK.Page.__init__ (self, template, **kwargs)


CTK.publish ('^%s/.+\.html'   %(URL_BASE), Render)
