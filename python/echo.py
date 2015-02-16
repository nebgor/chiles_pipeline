"""
Echo the arguments passed to a function
"""
import sys


def format_arg_value(arg_val):
    """ Return a string representing a (name, value) pair.

    >>> format_arg_value(('x', (1, 2, 3)))
    'x=(1, 2, 3)'
    """
    arg, val = arg_val
    return '{0}={1}'.format(arg, val)


def name(item):
    """ Return an item's name."""
    return item.__name__


def echo(fn):
    """ Echo calls to a function.

    Returns a decorated version of the input function which "echoes" calls
    made to it by writing out the function's name and the arguments it was
    called with.
    """
    import functools
    # Unpack function's arg count, arg names, arg defaults
    code = fn.func_code
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]
    fn_defaults = fn.func_defaults or list()
    argdefs = dict(zip(argnames[-len(fn_defaults):], fn_defaults))

    @functools.wraps(fn)
    def wrapped(*v, **k):
        # Collect function arguments by chaining together positional,
        # defaulted, extra positional and keyword arguments.
        positional = map(format_arg_value, zip(argnames, v))
        defaulted = [format_arg_value((a, argdefs[a]))
                     for a in argnames[len(v):] if a not in k]
        nameless = map(repr, v[argcount:])
        keyword = map(format_arg_value, k.items())
        print '{0}({1},{2},{3},{4})'.format(name(fn), positional, defaulted, nameless, keyword)
        return fn(*v, **k)
    return wrapped


def dump_all():
    """
    Dump all the inscope variables
    :return:
    """
    print '''
##### dump_all globals #####'''
    for xxx_module in list(sys.modules.keys()):
        for xxx_name in xxx_module.globals():
            if xxx_name != '__builtins__' and xxx_name != '__doc__':
                xxx_my_value = eval(xxx_name)
                print '{0}({1})\t=\t{2}'.format(xxx_name, type(xxx_name), xxx_my_value)

    print '''
##### dump_all locals #####'''
    for xxx_name in locals():
        if xxx_name != 'xxx_name' and xxx_name != 'xxx_my_value':
            xxx_my_value = eval(name)
            print '{0}({1})\t=\t{2}'.format(xxx_name, type(xxx_name), xxx_my_value)
    print '''
##### dump_all #####'''
