#!/usr/bin/python

import sys
from ovirt.node.config.defaults import NodeConfigFileSection, \
    OVIRT_NODE_DEFAULTS_FILENAME
from ovirt.node.utils.console import TransactionProgress
import inspect

from optparse import OptionParser

def list_funcs(cfg):
    def valid_member(x):
        return inspect.ismethod(x) and x.__name__.startswith("configure_")
    funcs = dict(inspect.getmembers(cfg, valid_member))
    return funcs

def print_func_usage(func, with_doc=True):
    argspec = inspect.getargspec(func)
    args = argspec.args[1:]
    txtargs = []
    for idx, arg in enumerate(args):
        defidx = idx - len(argspec.defaults) if argspec.defaults else -1
        if defidx >= 0:
            txtargs.append("[<%s=%s>]" % (arg.upper(),
                                          argspec.defaults[defidx]))
        else:
            txtargs.append("<%s>" % arg.upper())
    txtargs = " ".join(txtargs)
    if with_doc and inspect.getdoc(func):
        txtargs += "\n" + inspect.getdoc(func)
    return txtargs

def list_func_usage(func, customer_args):
    args = inspect.getargspec(func).args[1:]
    args_dict = {}
    for index, item in enumerate(customer_args):
        args_dict[args[index]] = item
    return args_dict

def list_classes(module):
    def valid_member(x):
        return inspect.isclass(x) and NodeConfigFileSection in x.mro()
    core = __import__(module, fromlist=[''])
    return dict(inspect.getmembers(core, valid_member))

def get_class(module, cls):
    mbs = list_classes(module)
    if cls not in mbs:
        raise RuntimeError("Unknown config obj: %s" % cls)
    return mbs[cls]

def wtf(module, classfunc, args=None, cfgfile=None, is_dry=False):
    cls, func = classfunc.split(".")
    cfg = get_class(module, cls)(cfgfile)
    funcs = list_funcs(cfg)

    # The function to run
    func = funcs[func]
    kwargs = list_func_usage(func, args)
    func(**kwargs)
    tx = cfg.transaction()
    TransactionProgress(tx, is_dry=is_dry).run()

def split_clsfunc(clsfunc):
    cls, func = clsfunc, None
    if "." in clsfunc:
        cls, func = clsfunc.split(".", 1)
    return (cls, func)

def more_usage():
    parser.print_help()
    print("\nAvailable classes in module '%s':" % options.module)
    for name in sorted(list_classes(options.module).keys()):
        print("- %s" % name)

if __name__ == "__main__":
    cfgfile = OVIRT_NODE_DEFAULTS_FILENAME

    usage = "%prog [options] help|run [<CLASS>[.<FUNC> [<ARG> [<ARG>] ...]]]]"
    parser = OptionParser(usage=usage)
    parser.add_option("-m", "--module", dest="module",
                      help="Module to use",
                      default="ovirt.node.config.defaults")
    parser.add_option("--dry", dest="is_dry",
                      action="store_true",
                      help="Enable dry mode",
                      default=False)
    parser.add_option("--config", dest="cfgfile",
                      help="Config file to use",
                      default=cfgfile)

    (options, args) = parser.parse_args()

    if len(args) <= 1:
        more_usage()
        raise SystemExit(1)


    cmd = args[0]

    # help
    if cmd[0] == "h":
        cls, func = split_clsfunc(args[1])
        print("Functions in class '%s':\n" % cls)
        cfg = get_class(options.module, cls)
        funcs = list_funcs(cfg)
        for name, func in sorted(funcs.items()):
            print("- %s %s" % (name, print_func_usage(func)))
        if not funcs:
            print("There are no documented functions in this class.")
            print("Please provide a patch to add documentation.")

    # run
    elif cmd[0] == "r":
        cls, params = args[1], args[2:]
        wtf(options.module, cls, params, options.cfgfile, options.is_dry)
    else:
        more_usage()
        raise SystemExit(2)
