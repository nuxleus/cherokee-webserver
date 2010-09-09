# -*- coding: utf-8 -*-
#
# Cherokee-admin
#
# Authors:
#      Alvaro Lopez Ortega <alvaro@alobbs.com>
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

import CTK

import os
import imp
import stat
import time
import tarfile
import traceback
import OWS_Login
import Install_Log
import SystemInfo

from util import *
from consts import *
from ows_consts import *
from configured import *

from XMLServerDigest import XmlRpcServer

PAYMENT_CHECK_TIMEOUT  = 5 * 1000 # 5 secs

NOTE_ALREADY_INSTALLED = N_('The application is already in your library, so there is no need the buy it again. Please, proceed to the installation.')
NOTE_ALREADY_TO_BUY_1  = N_('The application is available at the Octality Market. Please, check "Check Out" to proceed to the payment secction.')
NOTE_ALREADY_TO_BUY_2  = N_('The application will be downloaded and installed afterwards. It will also remain in your library for any future installation.')

THANKS_P1 = N_("The application has been deployed and Cherokee has been configured to fully support it. Remember to backup your configuration if you are going to manually perform further customization. You can always restore it or reinstall the application if anything does not work as expected.")
THANKS_P2 = N_("Thank you for buying at Octality's Market. We hope to see you back soon!")

URL_INSTALL_WELCOME        = "%s/install/welcome"        %(URL_MAIN)
URL_INSTALL_INIT_CHECK     = "%s/install/check"          %(URL_MAIN)
URL_INSTALL_PAY_CHECK      = "%s/install/pay"            %(URL_MAIN)
URL_INSTALL_DOWNLOAD       = "%s/install/download"       %(URL_MAIN)
URL_INSTALL_SETUP_INTRO    = "%s/install/setup-intro"    %(URL_MAIN)
URL_INSTALL_SETUP          = "%s/install/setup"          %(URL_MAIN)
URL_INSTALL_EXCEPTION      = "%s/install/exception"      %(URL_MAIN)
URL_INSTALL_SETUP_EXTERNAL = "%s/install/setup/package"  %(URL_MAIN)
URL_INSTALL_DOWNLOAD_ERROR = "%s/install/download_error" %(URL_MAIN)
URL_INSTALL_DONE           = "%s/install/done"           %(URL_MAIN)


class InstallDialog (CTK.Dialog):
    def __init__ (self, info):
        title = "%s: %s" %(_("Installation"), info['application_name'])

        CTK.Dialog.__init__ (self, {'title': title, 'width': 600, 'minHeight': 300})
        self.info = info

        for key in ('application_id', 'application_name', 'currency_symbol', 'amount', 'currency'):
            CTK.cfg['tmp!market!install!%s'%(key)] = str(info[key])

        self.refresh = CTK.RefreshableURL()
        self.druid = CTK.Druid(self.refresh)
        self.druid.bind ('druid_exiting', self.JS_to_close())

        self += self.druid

    def JS_to_show (self):
        js = CTK.Dialog.JS_to_show (self)
        js += self.refresh.JS_to_load (URL_INSTALL_WELCOME)
        return js


class Install_Stage:
    def __call__ (self):
        try:
            return self.__safe_call__()
        except Exception, e:
            # Log the exception
            exception_str = traceback.format_exc()
            print exception_str
            Install_Log.log ("EXCEPTION!\n" + exception_str)

            # Present an alternative response
            cont = Exception_Handler (exception_str)
            return cont.Render().toStr()


class Welcome (Install_Stage):
    def __safe_call__ (self):
        Install_Log.reset()
        Install_Log.log ("Retrieving package information..")

        box = CTK.Box()
        box += CTK.RawHTML ('<h2>%s</h2>' %(_('Connecting to Octality')))
        box += CTK.RawHTML ('<h1>%s</h1>' %(_('Retrieving package information..')))
        box += CTK.RawHTML (js = CTK.DruidContent__JS_to_goto (box.id, URL_INSTALL_INIT_CHECK))
        return box.Render().toStr()


class Initial_Check (Install_Stage):
    def __safe_call__ (self):
        app_id   = CTK.cfg.get_val('tmp!market!install!application_id')
        app_name = CTK.cfg.get_val('tmp!market!install!application_name')

        info = {'cherokee': VERSION,
                'system':   SystemInfo.get_info()}

        cont = CTK.Container()
        xmlrpc = XmlRpcServer (OWS_APPS_INSTALL, user=OWS_Login.login_user, password=OWS_Login.login_password)
        install_info = xmlrpc.get_install_info (app_id, info)

        if install_info['installable']:
            Install_Log.log ("Checking: %s, ID: %s = Installable, URL=%s" %(app_name, app_id, install_info['url']))

            CTK.cfg['tmp!market!install!download'] = install_info['url']

            cont += CTK.RawHTML ("<h2>%s</h2>"%(_('Application available')))
            cont += CTK.RawHTML ("<p>%s</p>"  %(_(NOTE_ALREADY_INSTALLED)))

            buttons = CTK.DruidButtonsPanel()
            buttons += CTK.DruidButton_Goto (_('Install'), URL_INSTALL_DOWNLOAD, False)
            cont += buttons
        else:
            Install_Log.log ("Checking: %s, ID: %s = Must check out first" %(app_name, app_id))

            cont += CTK.RawHTML ("<h2>%s %s</h2>"%(_('Checking out'), app_name))
            cont += CTK.RawHTML ("<p>%s</p>"  %(_(NOTE_ALREADY_TO_BUY_1)))
            cont += CTK.RawHTML ("<p>%s</p>"  %(_(NOTE_ALREADY_TO_BUY_2)))

            checkout = CTK.Button (_("Check Out"))
            checkout.bind ('click', CTK.JS.OpenWindow('%s/order/%s' %(OWS_STATIC, app_id)))
            checkout.bind ('click', CTK.DruidContent__JS_to_goto (checkout.id, URL_INSTALL_PAY_CHECK))

            buttons = CTK.DruidButtonsPanel()
            buttons += checkout
            cont += buttons

        return cont.Render().toStr()


class Pay_Check (Install_Stage):
    def __safe_call__ (self):
        app_id   = CTK.cfg.get_val('tmp!market!install!application_id')
        app_name = CTK.cfg.get_val('tmp!market!install!application_name')

        xmlrpc = XmlRpcServer (OWS_APPS_INSTALL, user=OWS_Login.login_user, password=OWS_Login.login_password)
        install_info = xmlrpc.get_install_info (app_id)

        Install_Log.log ("Waiting for the payment acknowledge..")

        box = CTK.Box()
        if not install_info['installable']:
            set_timeout_js = "setTimeout (reload_druid, %s);" %(PAYMENT_CHECK_TIMEOUT)
            box += CTK.RawHTML ("<h2>%s %s</h2>"%(_('Checking out'), app_name))
            box += CTK.RawHTML ('<h1>%s</h1>' %(_("Waiting for the payment acknowledge...")))
            box += CTK.RawHTML (js="function reload_druid() {%s %s}" %(CTK.DruidContent__JS_to_goto (box.id, URL_INSTALL_PAY_CHECK), set_timeout_js))
            box += CTK.RawHTML (js=set_timeout_js)
        else:
            Install_Log.log ("ACK!")
            box += CTK.DruidContent__JS_to_goto (box.id, URL_INSTALL_DOWNLOAD)
            CTK.cfg['tmp!market!install!download'] = install_info['url']

        return box.Render().toStr()


class Download (Install_Stage):
    def __safe_call__ (self):
        app_id       = CTK.cfg.get_val('tmp!market!install!application_id')
        app_name     = CTK.cfg.get_val('tmp!market!install!application_name')
        url_download = CTK.cfg.get_val('tmp!market!install!download')

        Install_Log.log ("Downloading %s" %(url_download))

        downloader = CTK.Downloader ('package', url_download)
        downloader.bind ('finished', CTK.DruidContent__JS_to_goto (downloader.id, URL_INSTALL_SETUP))
        downloader.bind ('error',    CTK.DruidContent__JS_to_goto (downloader.id, URL_INSTALL_DOWNLOAD_ERROR))

        cont = CTK.Container()
        cont += CTK.RawHTML ('<h2>%s %s</h2>' %(_("Downloading"), app_name))
        cont += CTK.RawHTML ('<p>%s</p>' %(_('The application is being downloaded. Hold on tight!')))
        cont += downloader
        cont += CTK.RawHTML (js = downloader.JS_to_start())
        return cont.Render().toStr()


class Download_Error (Install_Stage):
    def __safe_call__ (self):
        app_name = CTK.cfg.get_val('tmp!market!install!application_name')

        Install_Log.log ("Downloading Error: %s" %(url_download))

        cont = CTK.Container()
        cont += CTK.RawHTML ('<h2>%s %s</h2>' %(_("Downloading"), app_name))
        cont += CTK.RawHTML ("Say something else here") # TODO
        return cont.Render().toStr()


class Setup_Intro (Install_Stage):
    def __safe_call__ (self):
        app_name = CTK.cfg.get_val('tmp!market!install!application_name')

        Install_Log.log ("Set-up Error")

        box = CTK.Box()
        box += CKT.RawHTML ("<h2>%s</h2>" %(_("Setting up"), app_name))
        box += CKT.RawHTML ("<h1>%s</h1>" %(_("The application is being deployed...")))
        box += CTK.RawHTML (js = CTK.DruidContent__JS_to_goto (box.id, URL_INSTALL_SETUP))
        return box.Render().toStr()


def Exception_Handler_Apply():
    # Collect information
    info = {}
    info['log']      = Install_Log.get_full_log()
    info['user']     = OWS_Login.login_user
    info['comments'] = CTK.post['comments']
    info['platform'] = SystemInfo.get_info()
    info['tmp!market!install'] = CTK.cfg['tmp!market!install'].serialize()

    # Send it
    xmlrpc = XmlRpcServer (OWS_APPS_INSTALL, user=OWS_Login.login_user, password=OWS_Login.login_password)
    install_info = xmlrpc.report_exception (info)

    return {'ret': 'ok'}


class Exception_Handler (CTK.Box):
    def __init__ (self, exception_str):
        CTK.Box.__init__ (self)
        self += CTK.RawHTML ('<h2>%s</h2>' %(_("Internal Error")))
        self += CTK.RawHTML ('<h1>%s</h1>' %(_("An internal error occurred while deploying the application")))
        self += CTK.RawHTML ('<p>%s</p>' %(_("Information on the error has been collected so it can be reported and fixed up. Please help us improve it by sending the error information to the development team.")))

        thanks = CTK.Box ({'style': 'display:none'}, CTK.RawHTML (_('Thank you for your feedback! We do appreciate it.')))
        self += thanks

        report   = CTK.SubmitterButton (_("Report Issue"))
        comments = CTK.Box()
        comments += CTK.RawHTML ('%s:' %(_("Comments")))
        comments += CTK.TextArea ({'name': 'comments', 'rows':10, 'cols': 80, 'class': 'noauto'})

        submit = CTK.Submitter (URL_INSTALL_EXCEPTION)
        submit += comments
        submit += report
        self += submit

        submit.bind ('submit_success',
                     thanks.JS_to_show() + report.JS_to_hide() + comments.JS_to_hide())

        buttons = CTK.DruidButtonsPanel()
        buttons += CTK.DruidButton_Close(_('Close'))
        self += buttons


def replacement_cmd (command):
    # Collect information
    server_user  = CTK.cfg.get_val ('server!user',  'root')
    server_group = CTK.cfg.get_val ('server!group', 'root')
    app_root     = CTK.cfg.get_val ('tmp!market!install!root')
    root_group   = SystemInfo.get_info()['group_root']

    # Replacements
    command = command.replace('${web_user}',   server_user)
    command = command.replace('${web_group}',  server_group)
    command = command.replace('${app_root}',   app_root)
    command = command.replace('${root_group}', root_group)

    return command


class Setup (Install_Stage):
    def __safe_call__ (self):
        url_download = CTK.cfg.get_val('tmp!market!install!download')

        down_entry = CTK.DownloadEntry_Factory (url_download)
        package_path = down_entry.target_path

        # Create the local directory
        target_path = os.path.join (CHEROKEE_OWS_ROOT, str(time.time()))
        os.mkdir (target_path, 0700)
        CTK.cfg['tmp!market!install!root'] = target_path

        # Create the log file
        Install_Log.log ("Unpacking %s" %(package_path))
        Install_Log.set_file (os.path.join (target_path, "install.log"))

        # Uncompress
        tar = tarfile.open (package_path, 'r:gz')
        for tarinfo in tar:
            Install_Log.log ("  %s" %(tarinfo.name))
            tar.extract (tarinfo, target_path)

        # Set default permission
        Install_Log.log ("Setting default permission 711 for directory %s" %(target_path))
        os.chmod (target_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH )

        # Remove the package
        Install_Log.log ("Removing %s" %(package_path))
        os.unlink (package_path)

        # Import the Installation handler
        if os.path.exists (os.path.join (target_path, "installer.py")):
            Install_Log.log ("Passing control to installer.py")
            installer_path = os.path.join (target_path, "installer.py")
            pkg_installer = imp.load_source ('installer', installer_path)
        else:
            Install_Log.log ("Passing control to installer.pyo")
            installer_path = os.path.join (target_path, "installer.pyo")
            pkg_installer = imp.load_compiled ('installer', installer_path)

        # Set owner and permissions
        Install_Log.log ("Post unpack commands")

        for command_entry in pkg_installer.__dict__.get ('POST_UNPACK_COMMANDS',[]):
            command = replacement_cmd (command_entry['command'])
            Install_Log.log ("  %s" %(command))

            ret = run (command, stderr=True)
            if ret['stderr'] != 0:
                Install_Log.log ('    ' + ret['stderr'])

            if command_entry.get ('check_ret', True):
                None # TODO

        # Delegate to Installer
        box = CTK.Box()
        box += CTK.RawHTML (js = CTK.DruidContent__JS_to_goto (box.id, URL_INSTALL_SETUP_EXTERNAL))
        return box.Render().toStr()


class Install_Done (Install_Stage):
    def __safe_call__ (self):
        app_name = CTK.cfg.get_val('tmp!market!install!application_name')
        root     = CTK.cfg.get_val('tmp!market!install!root')

        # Finished
        f = open (os.path.join (root, "finished"), 'w+')
        f.close()

        Install_Log.log ("Finished")

        # Normalize CTK.cfg
        CTK.cfg.normalize ('vserver')

        # Thank user for the install
        box = CTK.Box()
        box += CTK.RawHTML ('<h2>%s %s</h2>' %(app_name, _("has been installed successfully")))
        box += CTK.RawHTML ("<p>%s</p>"    %(_(THANKS_P1)))
        box += CTK.RawHTML ("<p>%s</p>"    %(_(THANKS_P2)))

        buttons = CTK.DruidButtonsPanel()
        buttons += CTK.DruidButton_Close(_('Close'))
        box += buttons

        return box.Render().toStr()


CTK.publish ('^%s$'%(URL_INSTALL_WELCOME),        Welcome)
CTK.publish ('^%s$'%(URL_INSTALL_INIT_CHECK),     Initial_Check)
CTK.publish ('^%s$'%(URL_INSTALL_PAY_CHECK),      Pay_Check)
CTK.publish ('^%s$'%(URL_INSTALL_DOWNLOAD),       Download)
CTK.publish ('^%s$'%(URL_INSTALL_SETUP_INTRO),    Setup_Intro)
CTK.publish ('^%s$'%(URL_INSTALL_SETUP),          Setup)
CTK.publish ('^%s$'%(URL_INSTALL_DOWNLOAD_ERROR), Download_Error)
CTK.publish ('^%s$'%(URL_INSTALL_DONE),           Install_Done)
CTK.publish ('^%s$'%(URL_INSTALL_EXCEPTION),      Exception_Handler_Apply, method="POST")
