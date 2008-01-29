import imp, sys

class Module:
    def __init__ (self, id, cfg, prefix):
        self._id     = id
        self._cfg    = cfg
        self._prefix = prefix

def module_obj_factory (name, cfg, prefix):
    # Assemble module name
    mod_name = reduce (lambda x,y: x+y, map(lambda x: x.capitalize(), name.split('_')))

    # Load the module source file
    mod = imp.load_source (name, "Module%s.py" % (mod_name))
    sys.modules[name] = mod

    # Instance the object
    src = "mod_obj = mod.Module%s(cfg, prefix)" % (mod_name)
    exec(src)

    return mod_obj

if __name__ == "__main__":
    mod_obj = module_obj_factory("file", None)
    print mod_obj.Render()
