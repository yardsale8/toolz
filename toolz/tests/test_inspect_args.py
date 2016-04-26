import functools
import itertools
import operator
import sys
from toolz.functoolz import (curry, is_valid_args, is_partial_args, is_arity,
                             num_required_args, has_varargs, has_keywords)
from toolz._signatures import builtins
from toolz.compatibility import PY3
from toolz.utils import raises


def make_func(param_string, raise_if_called=True):
    if not param_string.startswith('('):
        param_string = '(%s)' % param_string
    if raise_if_called:
        body = 'raise ValueError("function should not be called")'
    else:
        body = 'return True'
    d = {}
    exec('def func%s:\n    %s' % (param_string, body), globals(), d)
    return d['func']


def test_make_func():
    f = make_func('')
    assert raises(ValueError, lambda: f())
    assert raises(TypeError, lambda: f(1))

    f = make_func('', raise_if_called=False)
    assert f()
    assert raises(TypeError, lambda: f(1))

    f = make_func('x, y=1', raise_if_called=False)
    assert f(1)
    assert f(x=1)
    assert f(1, 2)
    assert f(x=1, y=2)
    assert raises(TypeError, lambda: f(1, 2, 3))

    f = make_func('(x, y=1)', raise_if_called=False)
    assert f(1)
    assert f(x=1)
    assert f(1, 2)
    assert f(x=1, y=2)
    assert raises(TypeError, lambda: f(1, 2, 3))


def test_is_valid(check_valid=is_valid_args, incomplete=False):
    orig_check_valid = check_valid
    check_valid = lambda func, *args, **kwargs: orig_check_valid(func, args, kwargs)

    f = make_func('')
    assert check_valid(f)
    assert check_valid(f, 1) is False
    assert check_valid(f, x=1) is False

    f = make_func('x')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, x=2) is False
    assert check_valid(f, 1, y=2) is False
    assert check_valid(f, 1, 2) is False
    assert check_valid(f, x=1, y=2) is False

    f = make_func('x=1')
    assert check_valid(f)
    assert check_valid(f, 1)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, x=2) is False
    assert check_valid(f, 1, y=2) is False
    assert check_valid(f, 1, 2) is False
    assert check_valid(f, x=1, y=2) is False

    f = make_func('*args')
    assert check_valid(f)
    assert check_valid(f, 1)
    assert check_valid(f, 1, 2)
    assert check_valid(f, x=1) is False

    f = make_func('**kwargs')
    assert check_valid(f)
    assert check_valid(f, x=1)
    assert check_valid(f, x=1, y=2)
    assert check_valid(f, 1) is False

    f = make_func('x, *args')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1)
    assert check_valid(f, 1, 2)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, x=1) is False
    assert check_valid(f, 1, y=1) is False

    f = make_func('x, y=1, **kwargs')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, 2)
    assert check_valid(f, x=1, y=2, z=3)
    assert check_valid(f, 1, 2, y=3) is False

    f = make_func('a, b, c=3, d=4')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, 1, 2)
    assert check_valid(f, 1, c=3) is incomplete
    assert check_valid(f, 1, e=3) is False
    assert check_valid(f, 1, 2, e=3) is False
    assert check_valid(f, 1, 2, b=3) is False

    assert check_valid(1) is False


def test_is_valid_py3(check_valid=is_valid_args, incomplete=False):
    if not PY3:
        return
    orig_check_valid = check_valid
    check_valid = lambda func, *args, **kwargs: orig_check_valid(func, args, kwargs)

    f = make_func('x, *, y=1')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, y=2)
    assert check_valid(f, 1, 2) is False
    assert check_valid(f, 1, z=2) is False

    f = make_func('x, *args, y=1')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1)
    assert check_valid(f, x=1)
    assert check_valid(f, 1, y=2)
    assert check_valid(f, 1, 2, y=2)
    assert check_valid(f, 1, 2)
    assert check_valid(f, 1, z=2) is False

    f = make_func('*, y=1')
    assert check_valid(f)
    assert check_valid(f, 1) is False
    assert check_valid(f, y=1)
    assert check_valid(f, z=1) is False

    f = make_func('x, *, y')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, x=1) is incomplete
    assert check_valid(f, 1, y=2)
    assert check_valid(f, x=1, y=2)
    assert check_valid(f, 1, 2) is False
    assert check_valid(f, 1, z=2) is False
    assert check_valid(f, 1, y=1, z=2) is False

    f = make_func('x=1, *, y, z=3')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1, z=3) is incomplete
    assert check_valid(f, y=2)
    assert check_valid(f, 1, y=2)
    assert check_valid(f, x=1, y=2)
    assert check_valid(f, x=1, y=2, z=3)
    assert check_valid(f, 1, x=1, y=2) is False
    assert check_valid(f, 1, 3, y=2) is False

    f = make_func('w, x=2, *args, y, z=4')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, 1, y=3)

    f = make_func('a, b, c=3, d=4, *args, e=5, f=6, g, h')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, 1, 2) is incomplete
    assert check_valid(f, 1, 2, g=7) is incomplete
    assert check_valid(f, 1, 2, g=7, h=8)
    assert check_valid(f, 1, 2, 3, 4, 5, 6, 7, 8, 9) is incomplete

    f = make_func('a: int, b: float')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, b=1) is incomplete
    assert check_valid(f, 1, 2)

    f = make_func('(a: int, b: float) -> float')
    assert check_valid(f) is incomplete
    assert check_valid(f, 1) is incomplete
    assert check_valid(f, b=1) is incomplete
    assert check_valid(f, 1, 2)

    f.__signature__ = 34
    assert check_valid(f) is False

    class RaisesValueError(object):
        def __call__(self):
            pass
        @property
        def __signature__(self):
            raise ValueError('Testing Python 3.4')

    f = RaisesValueError()
    assert check_valid(f) is None


def test_is_partial():
    test_is_valid(check_valid=is_partial_args, incomplete=True)
    test_is_valid_py3(check_valid=is_partial_args, incomplete=True)


def test_is_valid_curry():
    def check_curry(func, args, kwargs, incomplete=True):
        try:
            curry(func)(*args, **kwargs)
            curry(func, *args)(**kwargs)
            curry(func, **kwargs)(*args)
            curry(func, *args, **kwargs)()
            if not isinstance(func, type(lambda: None)):
                return None
            return incomplete
        except ValueError:
            return True
        except TypeError:
            return False

    check_valid = functools.partial(check_curry, incomplete=True)
    test_is_valid(check_valid=check_valid, incomplete=True)
    test_is_valid_py3(check_valid=check_valid, incomplete=True)

    check_valid = functools.partial(check_curry, incomplete=False)
    test_is_valid(check_valid=check_valid, incomplete=False)
    test_is_valid_py3(check_valid=check_valid, incomplete=False)


def test_func_keyword():
    def f(func=None):
        pass
    assert is_valid_args(f, (), {})
    assert is_valid_args(f, (None,), {})
    assert is_valid_args(f, (), {'func': None})
    assert is_valid_args(f, (None,), {'func': None}) is False
    assert is_partial_args(f, (), {})
    assert is_partial_args(f, (None,), {})
    assert is_partial_args(f, (), {'func': None})
    assert is_partial_args(f, (None,), {'func': None}) is False


def test_has_unknown_args():
    assert has_varargs(1) is False
    assert has_varargs(map)
    assert has_varargs(make_func('')) is False
    assert has_varargs(make_func('x, y, z')) is False
    assert has_varargs(make_func('*args'))
    assert has_varargs(make_func('**kwargs')) is False
    assert has_varargs(make_func('x, y, *args, **kwargs'))
    assert has_varargs(make_func('x, y, z=1')) is False
    assert has_varargs(make_func('x, y, z=1, **kwargs')) is False

    if PY3:
        f = make_func('*args')
        f.__signature__ = 34
        assert has_varargs(f) is False

        class RaisesValueError(object):
            def __call__(self):
                pass
            @property
            def __signature__(self):
                raise ValueError('Testing Python 3.4')

        f = RaisesValueError()
        assert has_varargs(f) is None


def test_num_required_args():
    assert num_required_args(lambda: None) == 0
    assert num_required_args(lambda x: None) == 1
    assert num_required_args(lambda x, *args: None) == 1
    assert num_required_args(lambda x, **kwargs: None) == 1
    assert num_required_args(lambda x, y, *args, **kwargs: None) == 2
    assert num_required_args(map) == 2
    assert num_required_args(dict) is None


def test_has_keywords():
    assert has_keywords(lambda: None) is False
    assert has_keywords(lambda x: None) is False
    assert has_keywords(lambda x=1: None)
    assert has_keywords(lambda **kwargs: None)
    assert has_keywords(int)
    assert has_keywords(sorted)
    assert has_keywords(max)
    assert has_keywords(map) is False
    assert has_keywords(bytearray) is None


def test_has_varargs():
    assert has_varargs(lambda: None) is False
    assert has_varargs(lambda *args: None)
    assert has_varargs(lambda **kwargs: None) is False
    assert has_varargs(map)
    if PY3:
        assert has_varargs(max) is None


def test_is_arity():
    assert is_arity(0, lambda: None)
    assert is_arity(1, lambda: None) is False
    assert is_arity(1, lambda x: None)
    assert is_arity(3, lambda x, y, z: None)
    assert is_arity(1, lambda x, *args: None) is False
    assert is_arity(1, lambda x, **kwargs: None) is False
    assert is_arity(1, all)
    assert is_arity(2, map) is False
    assert is_arity(2, range) is None


def test_introspect_builtin_modules():
    mods = [builtins, functools, itertools, operator]

    blacklist = set()
    if hasattr(builtins, 'basestring'):
        blacklist.add(builtins.basestring)

    def is_missing(modname, name, func):
        if name.startswith('_') and not name.startswith('__'):
            return False
        try:
            if issubclass(func, BaseException):
                return False
        except TypeError:
            pass
        return (callable(func) and modname in func.__module__
                and is_partial_args(func, (), {}) is None
                and func not in blacklist)

    missing = {}
    for mod in mods:
        modname = mod.__name__
        for name, func in vars(mod).items():
            if is_missing(modname, name, func):
                if modname not in missing:
                    missing[modname] = []
                missing[modname].append(name)
    if missing:
        messages = []
        for modname, names in sorted(missing.items()):
            msg = '{}\n    {}'.format(modname, '\n    '.join(sorted(names)))
            messages.append(msg)
        message = 'Missing introspection for the following builtins:\n\n'
        raise AssertionError(message + '\n'.join(messages))

