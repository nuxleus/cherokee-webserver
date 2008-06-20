import validations

from Page import *
from Table import *
from Form import *
from consts import *
from CherokeeManagement import *

DATA_VALIDATION = [
    ("server!fdlimit",                validations.is_positive_int),
    ("server!pid_file",              (validations.parent_is_dir, 'cfg')),
    ("server!sendfile_min",           validations.is_positive_int),
    ("server!sendfile_max",           validations.is_positive_int),
    ('server!panic_action',          (validations.is_local_file_exists, 'cfg')),
    ('server!listen_queue',           validations.is_positive_int),
    ('server!max_connection_reuse',   validations.is_positive_int),
    ('server!log_flush_elapse',       validations.is_positive_int),
    ('server!keepalive_max_requests', validations.is_positive_int)
]

WARNING = """
<p><b>WARNING</b>: This section contains advanced configuration
parameters. It is recommended to not change anything unless you
really know what you are doing.</p>
"""

NOTE_THREAD       = 'Defines which thread policy the OS should apply to the server.'
NOTE_THREAD_NUM   = 'If empty, Cherokee will calculate a default number.'
NOTE_FD_NUM       = 'It defines how many file descriptors the server should handle. Default is the number showed by ulimit -n'
NOTE_POLLING      = 'Allows to choose the internal file descriptor polling method.'
NOTE_SENDFILE_MIN = 'Minimum size of a file to use sendfile(). Default: 32768 Bytes.'
NOTE_SENDFILE_MAX = 'Maximum size of a file to use sendfile(). Default: 2 GB.'
NOTE_PANIC_ACTION = 'Name a program that will be called if, by some reason, the server fails. Default: <em>cherokee-panic</em>.'
NOTE_PID_FILE     = 'Path of the PID file. If empty, the file will not be created.'
NOTE_LISTEN_Q     = 'Max. length of the incoming connection queue.'
NOTE_REUSE_CONNS  = 'Set the number of how many internal connections can be hold for reuse by each thread. Default 20.'
NOTE_FLUSH_TIME   = 'Sets the number of seconds between log consolidations (flushes). Default: 10 seconds.'
NOTE_KEEPALIVE_RS = 'Maximum number of HTTP requests that can be served by each keepalive connection.'


class PageAdvanced (PageMenu, FormHelper):
    def __init__ (self, cfg):
        PageMenu.__init__ (self, 'advanced', cfg)
        FormHelper.__init__ (self, 'advanced', cfg)

    def _op_render (self):
        content = self._render_content()
        self.AddMacroContent ('title', 'Advanced configuration')
        self.AddMacroContent ('content', content)
        return Page.Render(self)

    def _render_content (self):
        polling_methods = []
        for name, desc in POLL_METHODS:
            if ((not name) or \
                cherokee_has_polling_method (name)):
                polling_methods.append((name, desc))

        txt = "<h1>Advanced configuration</h1>"
        txt += self.Dialog(WARNING, 'warning')

        txt += "<h2>System tweaking</h2>"
        table = TableProps()
        self.AddPropEntry    (table, 'Thread Number',    'server!thread_number', NOTE_THREAD_NUM)
        self.AddPropOptions  (table, 'Thread Policy',    'server!thread_policy', THREAD_POLICY, NOTE_THREAD)
        self.AddPropEntry    (table, 'File descriptors', 'server!fdlimit', NOTE_FD_NUM)
        txt += self.Indent(table)

        txt += "<h2>Server tweaking</h2>"
        table = TableProps()
        self.AddPropOptions  (table, 'Polling Method',    'server!poll_method',  polling_methods, NOTE_POLLING)
        self.AddPropEntry    (table, 'Sendfile min size', 'server!sendfile_min', NOTE_SENDFILE_MIN)
        self.AddPropEntry    (table, 'Sendfile max size', 'server!sendfile_max', NOTE_SENDFILE_MAX)
        self.AddPropEntry    (table, 'Panic action',      'server!panic_action', NOTE_PANIC_ACTION)
        self.AddPropEntry    (table, 'PID file',          'server!pid_file',     NOTE_PID_FILE)
        txt += self.Indent(table)

        txt += "<h2>Server behaviour</h2>"
        table = TableProps()
        self.AddPropEntry    (table, 'Listening queue lenght', 'server!listen_queue',           NOTE_LISTEN_Q)
        self.AddPropEntry    (table, 'Reuse connections',      'server!max_connection_reuse',   NOTE_REUSE_CONNS)
        self.AddPropEntry    (table, 'Log flush time',         'server!log_flush_elapse',       NOTE_FLUSH_TIME)
        self.AddPropEntry    (table, 'Max keepalive reqs',     'server!keepalive_max_requests', NOTE_KEEPALIVE_RS)
        txt += self.Indent(table)

        form = Form ("/%s" % (self._id))
        return form.Render(txt,DEFAULT_SUBMIT_VALUE)
	
    def _op_apply_changes (self, uri, post):
        self.ApplyChanges ([], post, DATA_VALIDATION) 

