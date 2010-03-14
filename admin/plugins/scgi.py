# -*- coding: utf-8 -*-
#
# Cherokee-admin
#
# Authors:
#      Alvaro Lopez Ortega <alvaro@alobbs.com>
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

import CTK
import Cherokee
import validations
import CgiBase
import Balancer
from consts import *

HELPS = CgiBase.HELPS + [('modules_handlers_scgi', "SCGI")]

def commit():
    for k in CTK.post:
        del (CTK.cfg[k])
    return {'ret':'ok'}


class Plugin_scgi (CgiBase.PluginHandlerCGI):
    def __init__ (self, key, **kwargs):
        kwargs['show_script_alias']  = False
        kwargs['show_change_uid']    = False
        kwargs['show_document_root'] = True

        # CGI Generic
        CgiBase.PluginHandlerCGI.__init__ (self, key, **kwargs)
        CgiBase.PluginHandlerCGI.AddCommon (self)

        # Balancer
        modul = CTK.PluginSelector('%s!balancer'%(key), Cherokee.support.filter_available (BALANCERS))
        table = CTK.PropsTable()
        table.Add (_("Balancer"), modul.selector_widget, _(Balancer.NOTE_BALANCER))

        self += CTK.RawHTML ('<h2>%s</h2>' %(_('SCGI specific')))
        self += CTK.Indenter (table)
        self += modul