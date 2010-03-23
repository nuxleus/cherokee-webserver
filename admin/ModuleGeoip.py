from Form import *
from Table import *
from Module import *
from flags import *

import validations

# For gettext
N_ = lambda x: x

ISO3166_URL      = "http://www.iso.org/iso/country_codes/iso_3166_code_lists/english_country_names_and_code_elements.htm"
NOTE_NEW_COUNTRY = N_("Add the initial country. It's possible to add more later on.")
NOTE_ADD_COUNTRY = N_("Pick an additional country to add to the country list.")
NOTE_COUNTRIES   = N_("""List of countries from the client IPs. It must use the
<a target=\"_blank\" href=\"%s\">ISO 3166</a> country notation.""") % (ISO3166_URL)

class ModuleGeoip (Module, FormHelper):
    validation = [('tmp!new_rule!value', validations.is_safe_id_list)]

    def __init__ (self, cfg, prefix, submit_url):
        FormHelper.__init__ (self, 'geoip', cfg)
        Module.__init__ (self, 'geoip', cfg, prefix, submit_url)

    def _render_new_entry (self):
        cfg_key = '%s!value'%(self._prefix)
        flags = OptionFlags (cfg_key)
        button = '<input type="submit" value="%s" />' % (_('Add'))

        table = TableProps()
        self.AddProp (table, _('Country'), cfg_key, str(flags) + button, _(NOTE_NEW_COUNTRY))
        return str(table)

    def _render_modify_entry (self):
        cfg_key = '%s!countries'%(self._prefix)
        key_val = self._cfg.get_val (cfg_key, "")

        # Text entry
        table = TableProps()
        self.AddPropEntry (table, _('Countries'), cfg_key, _(NOTE_COUNTRIES))

        # Flags
        cfg_key_fake = 'tmp!add_county'
        flags = OptionFlags (cfg_key_fake)

        # Button
        button = '<input type="button" value="%s" onClick="flags_add_to_key(\'%s\',\'%s\',\'%s\',\'%s\');"/>' % (
                 _('Add'), cfg_key_fake, cfg_key, key_val, '/ajax/update')

        content = ADD_FLAGS_TO_KEY_JS + str(flags) + button
        self.AddProp (table, _('Add Country'), "", content, _(NOTE_ADD_COUNTRY))

        return str(table)

    def _op_render (self):
        if self._prefix.startswith('tmp!'):
            return self._render_new_entry()

        return self._render_modify_entry()

    def _op_apply_changes (self, uri, post):
        self.ApplyChangesPrefix (self._prefix, None, post)

    def apply_cfg (self, values):
        if not values.has_key('value'):
            print _("ERROR, a 'value' entry is needed!")

        cfg_key  = '%s!countries'%(self._prefix)
        contries = values['value']
        self._cfg[cfg_key] = contries

    def get_name (self):
        return self._cfg.get_val ('%s!countries'%(self._prefix))

    def get_type_name (self):
        return self._id.capitalize()