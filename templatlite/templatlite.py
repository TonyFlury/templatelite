#!/usr/bin/env python
# coding=utf-8
"""
# templating : Lightweight Templating system

Summary :
    A very lightweight templating system - suitable for simple html and python code

Use Case :
    I want a simple to use templating system so that I can easily create text & html

Testable Statements :
    ...
"""
from functools import wraps
import re
import six
import types

if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping

from .version import *

def registerModifier(name):
    """Helper function to register a modifier function"""
    def _outer(f):
        @wraps(f)
        def _wrapper(value, *args, **kwargs):
            return f(value, *args, **kwargs)
        Renderer._register_filter(name, _wrapper)
        return _wrapper
    return _outer

class UknownContextValue(Exception):
    pass

class UnrecognisedFilter(Exception):
    pass

class UnexpectedFilterArguments(Exception):
    pass

class Renderer(object):
    """General purpose simple template renderer"""
    _token_splitter_re = re.compile(r'({{.*?}}|{%.*?%}|{#.*?#})', flags=re.DOTALL)
    _split_args_re = re.compile(r"(?P<keyword>[a-zA-Z]\w*?:)?(?P<value>((\'.*?\')|((?<!\')[^:]+?))(?=\s|$))")
    _filters = {}

    _FILTER_SEP= '|'

    @classmethod
    def _register_filter(cls, name, function):
        """Register a named modifier - internal use only"""
        cls._filters[name] = function

    def __init__(self, template_str=None, errors=False, default=None):
        """A Template renderer
        :param template_str: The Template to render
        :param errors: A Boolean flag - True if errors in the template should
                        cause an exception
        :param default: The default value to insert into the template if an error
                        occurrs. If None the
        """
        self._template_str = template_str if template_str else ''
        self._segments = []
        self._errors = errors
        self._default = default
        self._source = ''
        self._render = self._compile( template_str )

    def _compile(self, template_str):
        """Compile a template into an executable function"""
        source = []

        indent = 4
        extend = False

        #Function boilerplate - define the function and setup standard modules
        source.append('def render(renderer, context):\n')
        source.append(' '*indent + 'segments=[]\n')
        source.append(' '*indent + 'segment_extend = segments.extend\n')
        source.append(' '*indent + 'segment_append = segments.append\n')

        # Break the temp
        split = self._token_splitter_re.split(self._template_str)
        for token in split:

            if not token:
                continue

            if token.startswith('{#'):
                continue

            if not token.startswith('{%'):
                 value = self._compile_context_variable(token) if token.startswith('{{') else repr(token)
                 if not extend:
                     source.append(' '*indent + 'segment_extend([')
                     extend = True
                 if extend:
                    source.append( value+',\n')

        if extend:
            source.append('])\n')
        source.append(' '*indent + 'return \'\'.join(segments)\n')
        self._source = ''.join(source)
        globals_source = {}
        try:
            six.exec_(self._source, globals_source,None)
            return globals_source['render']
        except Exception as e:
            six.raise_from(e,None)

    def _compile_context_variable(self, token, as_string=True):
        """Convert a context variable reference into a executable access

            3 cases :
            1) token is a filtered token
            2) token is the name of a local variable
            3) token is something else - maybe dotted
        """
        #Todo - needs to handle local variables too (ie from for loops)
        token = token[2:-2].strip()
        if self._FILTER_SEP in token:
            ret = self._compile_filtered_token(token)
        else:
            ret = 'renderer._dodots(\'' + token + '\',context)'

        return ('str('+ret+')') if as_string else ret

    def _dodots(self, token, context):
        """Process a expression - i.e. access to a data item within the context

           A wapper around self._resolvedots so that errors are dealt with as
           requested by the caller
        """
        assert isinstance(token, six.string_types)

        try:
            result = self._resolvedots(token, context)
        except UknownContextValue:
            if self._errors:
                raise
            else:
                return self._default if self._default else '{{'+token+'}}'
        except Exception as e:
                raise e
        else:
            return result

    def _resolvedots(self, token, context):
        """convert a dotted token into an actual value

           Process a dotted value - where each node is either :

           1) A key to a Mapping of some form
           2) An attribute name on an object
           3) A callable on an object

           It is allowed that the attribute or callable need not be the leaf node,
           so long as the value of the attribute or returned by the callable is valid
           for the subsquent nodes.
        """
        current_value = context
        for subitem in token.split('.'):
            if isinstance(current_value, Mapping):
                try:
                    current_value = current_value[subitem]
                    continue
                except KeyError:
                    six.raise_from(UknownContextValue('Unknown context variable \'{}\''.format(
                                    token)), None)

            if hasattr(current_value, subitem):
                if callable(getattr(current_value, subitem)):
                    current_value =  str(getattr(current_value, subitem)())
                    continue
                else:
                    current_value = str(getattr(current_value, subitem))
                    continue
            else:
                six.raise_from(UknownContextValue('Unknown context variable \'{}\''.format(
                        token)), None)
        else:
            return str(current_value)

    def _compile_filtered_token(self, token):
        """Compile a context variable access with a filter

           Handles filter with and without args
        """
        id, filter = token.split(self._FILTER_SEP)

        #Split off any arguments
        if ' ' in filter:
            filter,args = filter[:filter.find(' ')], filter[filter.find(' ')+1:]
        else:
            filter, args = filter, None

        pargs, kwargs = self._split_args(args) if args else ((),{})

        if filter in self.__class__._filters:
            try:
                return self.__class__._filters[filter](id, *pargs, **kwargs)
            except UnexpectedFilterArguments:
                six.raise_from(UnexpectedFilterArguments('Unexpected filter arguments in \'{}\''.format(token)),None)
        else:
            six.raise_from(UnrecognisedFilter('Unknown filter \'{}\''.format(filter)), None)

        #Todo Extend for publicly defined filters ?

    def _split_args(self, args):
        """Convert filter arguments into positional and keyword arguments"""
        matches = [m for m in self._split_args_re.finditer(args)]
        p_args = tuple([m.group('value') for m in matches if m.group('keyword') is None])
        kw_args = dict([(m.group('keyword'),str(m.group('value'))) for m in matches if m.group('keyword') is not None])
        return p_args, kw_args

    def from_context(self, *contexts):
        """Public I/f Render the template based on one or more dictionaries"""
        this_context = {}
        for context in contexts:
            this_context.update(context)

        if not self._render:
            return None
        return self._render( self, this_context)

@registerModifier('len')
def variable_length( id, *args, **kwargs):
    """Returns a compiled call to len"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return 'len(str(renderer._dodots(\''+id + '\',context)))'

@registerModifier('upper')
def variable_upper( id, *args, **kwargs ):
    """Returns a compiled call to upper"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return 'str(renderer._dodots(\''+id + '\',context)).upper()'

@registerModifier('lower')
def variable_lower( id,  *args, **kwargs):
    """Returns a compiled call to lower"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return 'str(renderer._dodots(\''+id + '\',context)).lower()'

@registerModifier('title')
def variable_title( id,  *args, **kwargs):
    """Returns a compiled call to .title"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return 'str(renderer._dodots(\''+id + '\',context)).title()'

@registerModifier('capitalize')
def variable_capitalize(id,  *args, **kwargs):
    """Returns a compiled call to capitalize"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return 'str(renderer._dodots(\''+id + '\',context)).capitalize()'

@registerModifier('split')
def variable_split(id,  *args, **kwargs):
    """Returns a compiled call to capitalize"""
    if len(args) >1 or kwargs:
        raise UnexpectedFilterArguments
    return 'str(renderer._dodots(\''+id + '\',context)).split(' + (repr(args[0]) if args else '') + ')'