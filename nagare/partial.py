# --
# Copyright (c) 2008-2017 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

"""Serializable partial functions"""

import sys
import types
import pickle
import copy_reg
from functools import partial

try:
    import stackless  # noqa: F401
except ImportError:
    def pickle_method(m):
        """Serialize a method

        In:
          - ``m`` -- method to pickle

        Return:
          - tuple to pickle (class of the method, name of the method, self)
        """
        return unpickle_method, (m.im_class, m.__name__, m.im_self)

    def unpickle_method(cls, name, o):
        """Deserialize a method

        In:
          - ``cls`` -- class of the method
          - ``name`` -- name of the method
          - ``o`` -- self

        Return:
          - the method, bound to ``o``
        """
        return getattr(o if isinstance(o, type) else cls, name).__get__(o, cls)

    copy_reg.pickle(types.MethodType, pickle_method)

    def pickle_function(f):
        """Serialize a function

        Only called when a lambda must be serialized

        In:
          - ``f`` -- function to pickle
        """
        msg = "Can't pickle %r, file \"%s\", line %d" % (f, f.func_code.co_filename, f.func_code.co_firstlineno)
        raise pickle.PicklingError(msg)

    copy_reg.pickle(types.FunctionType, pickle_function)


# -----------------------------------------------------------------------------

def max_number_of_args(nb):
    """Limit the number of positional parameters

    In:
      - ``nb`` - max number of positional parameters passed to ``f``. Other
                 positional parameters will be passed as the ``args`` tuple
    """
    def _(f):
        return lambda *args, **kw: f(*args[:nb], args=args[nb:], **kw)
    return _


# -----------------------------------------------------------------------------

def Partial(__f, *args, **kw):
    """Don't double wrap a ``partial()`` object if not needed"""
    return partial(__f, *args, **kw) if (not isinstance(__f, partial) or args or kw) else __f


# -----------------------------------------------------------------------------

class Decorator(object):
    """Use a ``partial()`` to decorate a function
    """
    def __init__(self, f, new_f, *args, **kw):
        """Decorate a function or a method

        In:
          - ``f`` -- function or method to decorate
          - ``new_f`` -- function that will decorate ``f``
          - ``args``, ``kw`` -- ``new_f`` parameters
        """

        # Hack:
        #  - change the name of ``f``
        #  - attach ``f`` to the global scope of its module
        #    (needed to be able to serialize it)
        m = sys.modules[f.__module__]
        f.__name__ = '__' + f.__name__
        setattr(m, f.__name__, f)

        self.f = f
        self.new_f = new_f
        self.args = args
        self.kw = kw

    def create_partial(self, o=None):
        """Create a ``_Partial()`` to call ``new_f``

        ``new_f`` will be called with the parameters:

          - ``self`` (``None`` if ``f`` is a function)
          - ``f``
          - ``args``, ``kw``
        """
        return Partial(self.new_f, o, self.f, *self.args, **self.kw)

    def __get__(self, o, cls):
        """Called when this decorator decorates a method
        """
        return self.create_partial(o)

    def __call__(self, *args, **kw):
        """Called when this decorator decorates a function
        """
        return self.create_partial()(*args, **kw)
