from Page import *
from Table import *
from Entry import *
from Form import *
from validations import *

DATA_VALIDATION = [
    ("server!mime_files", validate_path_list),
]

class PageMime (PageMenu):
    def __init__ (self, cfg):
        PageMenu.__init__ (self, cfg)
        self._id  = 'mime'

    def _op_handler (self, uri, post):
        if uri.startswith('/update'):
            return self._op_update (post)
        raise 'Unknown method'

    def _op_render (self):
        content = self._render_icon_list()

        self.AddMacroContent ('title', 'Mime types configuration')
        self.AddMacroContent ('content', content)

        return Page.Render(self)

    def _op_update (self, post):
        self.ValidateChanges (post, DATA_VALIDATION)

        # Add keys to configuration
        for key in post:
            value = post[key][0]
            print key, '=', value
            if value:
                self._cfg[key] = value
            else:
                del(self._cfg[key])
        # Return the URL
        return "/%s" % (self._id)

    def _render_icon_list (self):
        table = Table(2, 1)
        self.AddTableEntry (table, 'Files', 'server!mime_files')

        txt  = '<h2>System-wide MIME types file</h2>'        
        txt += str(table)

        form = Form ('%s/update' % (self._id))
        return form.Render(txt)
