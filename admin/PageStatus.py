# -*- coding: utf-8 -*-
#
# Cherokee-admin
#
# Authors:
#      Alvaro Lopez Ortega <alvaro@alobbs.com>
#      Taher Shihadeh <taher@unixwars.com>
#
# Copyright (C) 2001-2010 Alvaro Lopez Ortega
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
import CTK
import Page
import Graph
import Cherokee
import validations
import SelectionPanel

from CTK.Submitter import HEADER as Submit_HEADER
from configured import *

URL_BASE  = '/status'

# Help entries
HELPS = [('config_status', N_("Status"))]


class LiveLogs_Instancer (CTK.Container):
    class LiveLogs (CTK.Box):
        def __init__ (self, refreshable, vserver = None, **kwargs):
            CTK.Box.__init__ (self, **kwargs)

            self.refreshable = refreshable
            self.vserver     = vserver

    def __init__ (self, vserver):
        CTK.Container.__init__ (self)

        # Refresher
        refresh = CTK.Refreshable ({'id': 'log-area'})
        refresh.register (lambda: self.LiveLogs(refresh, vserver).Render())
        self += refresh


class Render_Content (CTK.Container):
    def __call__ (self, vsrv = None):
        cont = CTK.Container()

        if CTK.request.url.endswith('/general'):
            vsrv_nam = None
            cont += CTK.RawHTML ('<h1>%s</h1>' %(_('Server monitoring')))
        else:
            vsrv_num = CTK.request.url.split('/')[-1]
            vsrv_nam = CTK.cfg.get_val ("vserver!%s!nick" %(vsrv_num), _("Unknown"))
            cont += CTK.RawHTML ('<h1>%s: %s</h1>' %(_('Virtual Server Monitoring'), vsrv_nam))

        if CTK.cfg.get_val('server!collector') == 'rrd':
            cont += CTK.RawHTML('<h2>%s</h2>' %(_('Graphs')))

            if vsrv_nam:
                cont += CTK.Indenter(Graph.GraphVServer_Instancer(vsrv_nam))
            else:
                cont += CTK.Indenter(Graph.GraphServer_Instancer())

        #cont += CTK.RawHTML('<h2>%s</h2>' %(_('Live logs')))
        #cont += CTK.Indenter(LiveLogs_Instancer (vsrv_num))

        render = cont.Render()
        return render.toJSON()


class Render():
    class PanelList (CTK.Container):
        def __init__ (self, right_box):
            CTK.Container.__init__ (self)

            # Sanity check
            if not CTK.cfg.keys('vserver'):
                CTK.cfg['vserver!1!nick']           = 'default'
                CTK.cfg['vserver!1!document_root']  = '/tmp'
                CTK.cfg['vserver!1!rule!1!match']   = 'default'
                CTK.cfg['vserver!1!rule!1!handler'] = 'common'

            # Helpers
            entry   = lambda klass, key: CTK.Box ({'class': klass}, CTK.RawHTML (CTK.cfg.get_val(key, '')))
            special = lambda klass, txt: CTK.Box ({'class': klass}, CTK.RawHTML (txt))

            # Build the panel list
            panel = SelectionPanel.SelectionPanel (None, right_box.id, URL_BASE, '', container='vservers_panel')
            self += panel

            # Build the Virtual Server list
            vservers = CTK.cfg.keys('vserver')
            vservers.sort (lambda x,y: cmp(int(x), int(y)))
            vservers.reverse()

            # Special Panel entries
            content = [special('nick',  _('General')),
                       special('droot', _('System wide status'))]
            panel.Add ('general', '%s/content/general'%(URL_BASE), content, draggable=False)

            # Regular list entries
            for k in vservers:
                content = [entry('nick',  'vserver!%s!nick'%(k)),
                           entry('droot', 'vserver!%s!document_root'%(k))]

                panel.Add (k, '%s/content/%s'%(URL_BASE, k), content, draggable=False)


    def __call__ (self):
        title = _('Virtual Servers')

        # Content
        left  = CTK.Box({'class': 'panel'})
        left += CTK.RawHTML('<h2>%s</h2>'%(title))

        right = CTK.Box({'class': 'vserver_content'})
        left += CTK.Box({'class': 'filterbox'}, CTK.TextField({'class':'filter', 'optional_string': _('Virtual Server Filtering'), 'optional': True}))
        left += CTK.Box ({'id': 'vservers_panel'}, self.PanelList(right))

        # Build the page
        page = Page.Base(title, body_id='status', helps=HELPS, headers=Submit_HEADER)
        page += left
        page += right

        return page.Render()


CTK.publish (r'^%s$'               %(URL_BASE), Render)
CTK.publish ('^%s/content/[\d]+$'  %(URL_BASE), Render_Content)
CTK.publish ('^%s/content/general$'%(URL_BASE), Render_Content)
