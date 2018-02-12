#!/usr/bin/env python
# coding=utf-8
"""
# templatelite : Lightweight Templating system

Summary :
    A very lightweight templatelite system - suitable for simple html and python code

Use Case :
    I want a simple to use templating system so that I can easily create text & html

Testable Statements :
    ...
"""
from collections import deque as deque
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

class UnknownContextValue(Exception):
    """Raised when a Context Variable does not exist. This is the dot separated version of the variable name"""
    pass

class UnrecognisedFilter(Exception):
    """Raised when a filter is invoked on a Context Variable, but the filter is not recognised."""
    pass

class UnexpectedFilterArguments(Exception):
    """Raised when arguments are provided for a given filter, but where those arguments were not unexpected."""
    pass

class TemplateSyntaxError(Exception):
    """Raised when the template does not meet the expected syntax - this will be caused by an missing or unexpected directive"""
    pass

class Renderer(object):
    """A General purpose Template renderer

        :param template_str: The Template to render
        :param errors: A Boolean flag - True if errors in the template should
                    cause an exception
        :param default: The default value to insert into the template if an error
                    occurrs.
        :param remove_indentation: Whether or not to remove the left margin indentation.

        By using the default values from the class, any data access error in a ``ContextVariable`` will
        cause that context Variable to be rendered into the template as the unconverted context variable name.
        Errors in accessing data within for loops or if conditions then the value of None is used.

        if ``default`` is set then this string is used under error conditions (rather than the context variable name)

        If ``errors`` is set then any error within the template will cause a ``UnknownContextValue``, ``UnrecognisedFilter`` or ``UnexpectedFilterArguments`` exception as appropriate.

        The ``remove_indentation`` flag will strip all left margin indentation from the template as it renders. This setting is suitable for templates
        where any identation is inconsequatial (e.g. html). If the template is intended to create output where indentation needs to be preserved (Restructured Text (.rst), Python Source Code (.py) then ``remove_indentation`` needs to set to false).
    """
    # Split template into tokens surrounded by {{ }}, {% %}, or {# #}
    _token_splitter_re = re.compile(r'({{.*?}}|[ \t]*{%.*?%}\n|{#.*?#}|\n)', flags=re.DOTALL)

    # Split arguments out for filters
    _split_args_re = re.compile(r"(?P<keyword>[a-zA-Z]\w*?:)?(?P<value>((\'.*?\')|((?<!\')[^:]+?))(?=\s|$))")

    # Parse the target and iterables for a for loop, if statement and if else
    _for_parse_re = re.compile(r"^for\s+?(?P<target>.+)\s+?in\s+(?P<iterable>.+)$")
    _if_parse_re = re.compile(r'if\s+?(?P<expression>.+)$')
    _elif_parse_re = re.compile(r'elif\s+?(?P<expression>.+)$')

    # Find variables within expressions - name.name.name|name is valid
    _variable_re = re.compile(r'\b(?P<Variable>(?<!\'>)([a-zA-Z]\w*)(\.[a-zA-Z]\w*)*([|][a-zA-Z]\w*){0,1}(?!\')(?=\W|$))')

    _filters = {}

    _FILTER_SEP= '|'

    def __init__(self, template_str=None, errors=False, default=None, remove_indentation=True):
        """A General purpose Template renderer

            :param template_str: The Template to render
            :param errors: A Boolean flag - True if errors in the template should
                        cause an exception
            :param default: The default value to insert into the template if an error
                        occurrs. If None the
        """
        self._indent = 4
        self._extend = False
        self._source_parts = []
        self._source = None
        self._errors = errors

        self._template_str = template_str if template_str else ''
        self._errors = errors
        self._ignore_indentation = remove_indentation
        self._default = default
        self._render = self._compile()

    @classmethod
    def _register_filter(cls, name, function):
        """Register a named modifier - internal use only"""
        cls._filters[name] = function

    def _end_block(self, dedent=False):
        if self._extend:
            self._source_parts.append('])\n')
        self._extend = False
        if dedent:
            self._indent -= 4

    def _start_block(self, indent=False):
        if indent:
            self._indent += 4

    def _compile_expression(self, expression_text):
        s = ''
        last_end = 0
        for match in self._variable_re.finditer(expression_text):
            to = match.start('Variable')
            s += expression_text[last_end:to]
            var = match.group('Variable')
            if var in ['in','is','not','True','False','and','or','xor','lambda']:
                s += var
            else:
                s += self._compile_context_variable(var, as_string=False)
            last_end = match.end('Variable')
        else:
            s += expression_text[last_end:]
        return s

    def _compile_if(self, statement_token):
        m = self._if_parse_re.match(statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Invalid if statement \'{{% {} %}}\''.format(
                        statement_token)), None)
        expression = self._compile_expression(m.group('expression'))
        self._block_stack.append(('if',None))
        self._end_block()
        self._source_parts.append(' '* self._indent + 'if {}'.format(expression) + ':\n')
        self._start_block(indent=True)

    def _compile_elif(self, statement_token):
        start_block = self._block_stack.pop()
        if start_block[0] != 'if':
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% elif %}}\' expected \'{{% if %}}\''), None)
        m = self._elif_parse_re.match(statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Invalid elif statement \'{{% {} %}}\''.format(
                        statement_token)), None)
        expression = self._compile_expression(m.group('expression'))
        self._block_stack.append(('elif',None))
        self._end_block(dedent=True)
        self._source_parts.append(' '* self._indent + 'elif {}'.format(expression) + ':\n')
        self._start_block(indent=True)

    def _compile_endif(self, token):
        start_block = self._block_stack.pop()
        if start_block[0] == 'if' or start_block[0] == 'elif':
            self._end_block(dedent=True)
        else:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% endif %}}\' expected \'{{% endfor %}}\''.format(
                    token)), None)

    def _compile_else(self, token):
        if len(self._block_stack) == 0:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% else %}}\' without if or for'.format(
                    token)), None)

        start_block = self._block_stack.pop()
        if start_block[0] == 'if' or start_block[0] == 'elif' or start_block[0] == 'for':
            if start_block[1] == 'else':
                six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Unexpected directive - found \'{{% else %}}\' expected \'{{% endif %}}\''.format(
                        token)), None)

            self._end_block(dedent=True)
            self._source_parts.append(' ' * self._indent + 'else'+ ':\n')
            self._block_stack.append((start_block[0], 'else'))
            self._start_block(indent=True)

    def _compile_for(self, for_statement_token):
        m = self._for_parse_re.match(for_statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Invalid for statement \'{{% {} %}}\''.format(
                    for_statement_token)), None)

        targets = m.group('target').split(',')
        for target in targets:
            target = target.strip()
            if '.' in target or self._FILTER_SEP in target:
                six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Invalid target in for loop \'{}\''.format(
                        target)), None)

        self._block_stack.append(('for', None))
        self._locals.add(m.group('target'))
        self._end_block()
        self._source_parts.append(' ' * self._indent + 'for {targets} in {iterable}:\n'.format(
                            targets=m.group('target'),
                            iterable=self._compile_expression(m.group('iterable'))))
        self._start_block(indent=True)

    def _compile_endfor(self, token):
        last_token = self._block_stack.pop()
        if last_token[0] == 'for':
            self._end_block(dedent=True)
        else:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected token - found \'endfor\' expected \'endif\''.format(
                    token)), None)

    def _compile_block(self, token_stream):

        self._start_block()
        self._extend = False
        prev_token = ''
        for token in token_stream:

            if not token:
                continue

            if token.startswith('{#'):
                continue

            if token.strip().startswith('{%'):
                inner_token = token.strip()[2:-2].strip()
                if inner_token[:3] == 'for':
                    self._compile_for(inner_token)
                    continue

                if inner_token == 'endfor':
                    self._compile_endfor(inner_token)
                    continue

                if inner_token[:2] == 'if':
                    self._compile_if(inner_token)
                    continue

                if inner_token[:4] == 'elif':
                    self._compile_elif(inner_token)
                    continue

                if inner_token == 'endif':
                    self._compile_endif(inner_token)
                    continue

                if inner_token == 'else':
                    self._compile_else(inner_token)
                    continue

                if inner_token in ['break','continue']:
                    if ('for',None) not in self._block_stack:
                        six.raise_from(TemplateSyntaxError('Syntax Error : \'{{% {} %}}\' directive found outside loop'.format(inner_token)),None)
                    self._end_block()
                    self._source_parts.append(' ' * self._indent +inner_token + '\n')
                    continue

                six.raise_from(TemplateSyntaxError('Syntax Error : Unexpected directive : {}'.format(inner_token)), None)

            if token.startswith('{{'):
                value = self._compile_context_variable(token[2:-2])
            else:
                value = repr(
                    token if not self._ignore_indentation else token.lstrip(
                        ' \t'))

            if not self._extend:
                self._source_parts.append(
                    ' ' * self._indent + 'segment_extend([')
                self._extend = True
            if self._extend:
                self._source_parts.append('str({})'.format(value) + ',')

            prev_token = token

        if self._extend:
            self._source_parts.append('])\n')

    def _compile(self):
        """Compile a template into an executable function"""
        source = []

        indent = 4
        self._extend = False
        self._locals = set()
        self._block_stack = deque()

        # Function boilerplate - define the function and setup standard modules
        self._source_parts.append('def render(renderer, context):\n')
        self._source_parts.append(' ' * indent + 'segments=[]\n')
        self._source_parts.append(
            ' ' * indent + 'segment_extend = segments.extend\n')
        self._source_parts.append(
            ' ' * indent + 'segment_append = segments.append\n')

        # Break the temp in a steam of tokens
        tokens = (x for x in self._token_splitter_re.split(self._template_str))

        self._compile_block(tokens)

        if len(self._block_stack) != 0:
            last_token = self._block_stack.pop()
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Missing directive \'{{% end{} %}}\''.format(
                    last_token[0])), None)

        self._source_parts.append(
            ' ' * indent + 'return \'\'.join(segments)\n')
        self._source = ''.join(self._source_parts)
        globals_source = {}
        try:
            six.exec_(self._source, globals_source, None)
            return globals_source['render']
        except Exception as e:
            six.raise_from(e, None)

    def _compile_context_variable(self, token, as_string=True):
        """Convert a context variable reference into a executable access

            3 cases :
            1) token is a filtered token
            2) token is the name of a local variable
            3) token is something else - maybe dotted
        """
        token = token.strip()

        if token in self._locals:
            return token

        if self._FILTER_SEP in token:
            ret = self._compile_filtered_token(token)
        else:
            ret = 'renderer._dodots({!r},context, as_string={!r})'.format(token,as_string)

        return ('str(' + ret + ')') if as_string else ret

    def _dodots(self, token, context, as_string=True):
        """Process a expression - i.e. access to a data item within the context

           A wapper around self._resolvedots so that errors are dealt with as
           requested by the caller
           :param as_string:
        """
        assert isinstance(token, six.string_types)

        if token in self._locals:
            return token

        try:
            result = self._resolvedots(token, context)
        except UnknownContextValue:
            if self._errors:
                raise
            else:
                if not as_string:
                    return None
                return self._default if self._default else '{{' + token + '}}'
        except Exception as e:
            raise e
        else:
            return str(result) if as_string else result

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
                    six.raise_from(UnknownContextValue(
                        'Unknown context variable \'{}\''.format(
                            token)), None)

            if hasattr(current_value, subitem):
                if callable(getattr(current_value, subitem)):
                    current_value = str(getattr(current_value, subitem)())
                    continue
                else:
                    current_value = str(getattr(current_value, subitem))
                    continue
            else:
                six.raise_from(UnknownContextValue(
                    'Unknown context variable \'{}\''.format(
                        token)), None)
        else:
            return current_value

    def _compile_filtered_token(self, token):
        """Compile a context variable access with a filter

           Handles filter with and without args
        """
        id, filter = token.split(self._FILTER_SEP)

        # Split off any arguments
        if ' ' in filter:
            filter, args = filter[:filter.find(' ')], filter[
                                                      filter.find(' ') + 1:]
        else:
            filter, args = filter, None

        pargs, kwargs = self._split_args(args) if args else ((), {})

        if filter in self.__class__._filters:
            try:
                return self.__class__._filters[filter](id, *pargs, **kwargs)
            except UnexpectedFilterArguments:
                six.raise_from(UnexpectedFilterArguments(
                    'Unexpected filter arguments in \'{}\''.format(token)),
                               None)
        else:
            six.raise_from(
                UnrecognisedFilter('Unknown filter \'{}\''.format(filter)),
                None)

        # Todo Extend for publicly defined filters ?

    def _split_args(self, args):
        """Convert filter arguments into positional and keyword arguments"""
        matches = [m for m in self._split_args_re.finditer(args)]
        p_args = tuple(
            [m.group('value') for m in matches if m.group('keyword') is None])
        kw_args = dict(
            [(m.group('keyword'), str(m.group('value'))) for m in matches if
             m.group('keyword') is not None])
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
    return 'len(str(renderer._dodots({!r},context)))'.format(id)

@registerModifier('split')
def variable_split(id,  *args, **kwargs):
    """Returns a compiled call to capitalize"""
    if len(args) >1 or kwargs:
        raise UnexpectedFilterArguments
    split_arg = (args[0],) if args else tuple()
    print(split_arg)
    return 'renderer._dodots({!r},context).split({!r})'.format(id,*(split_arg) )

@registerModifier('cut')
def variable_split(id,  *args, **kwargs):
    """Returns a compiled call to capitalize"""
    if 0 > len(args) > 1 or kwargs:
        raise UnexpectedFilterArguments
    return 'renderer._dodots({!r},context).replace({!r})'.format( id, args[0])

#To Do Test cut, implement center, date and other filters

#Todo Rework Filter system to allow registration of filters