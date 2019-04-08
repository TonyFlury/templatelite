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

if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping


def registerModifier(name):
    """Helper function to register a modifier function"""

    def _outer(f):
        @wraps(f)
        def _wrapper(value, *args, **kwargs):
            return f(value, *args, **kwargs)

        Renderer.register_filter(name, _wrapper)
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
                    occurs.
        :param remove_indentation: Whether or not to remove the left margin indentation.

        By using the default values from the class, any data access error in a ``ContextVariable`` will
        cause that context Variable to be rendered into the template as the unconverted context variable name.
        Errors in accessing data within for loops or if conditions then the value of None is used.

        if ``default`` is set then this string is used under error conditions (rather than the context variable name)

        If ``errors`` is set then any error within the template will cause a ``UnknownContextValue``, ``UnrecognisedFilter`` or ``UnexpectedFilterArguments`` exception as appropriate.

        The ``remove_indentation`` flag will strip all left margin indentation from the template as it renders. This setting is suitable for templates
        where any indentation is inconsequential (e.g. html). If the template is intended to create output where indentation needs to be preserved (Restructured Text (.rst), Python Source Code (.py) then ``remove_indentation`` needs to set to false).
    """
    # Split template into tokens surrounded by {{ }}, {% %}, or {# #}
    _token_splitter_re = re.compile(r'({{.*?}}|[ \t]*{%.*?%}|{#.*?#}|)',
                                    flags=re.DOTALL)

    # Split arguments out for filters
    _split_args_re = re.compile(
        r"(?P<keyword>[a-zA-Z]\w*?:)?(?P<value>((\'.*?\')|((?<!\')[^:]+?))(?=\s|$))")

    # Parse the target and iterables for a for loop, if statement and if else
    _for_parse_re = re.compile(
        r"^for\s+?(?P<target>.+)\s+?in\s+(?P<iterable>.+?)(%})")
    _if_parse_re = re.compile(r'if\s+?(?P<expression>.+?)(%})')
    _elif_parse_re = re.compile(r'elif\s+?(?P<expression>.+?)(%})')

    # Find variables within expressions - name.name.name|name is valid
    _variable_re = re.compile(
        r'\b(?P<Variable>(?<!\'>)([a-zA-Z]\w*)(\.[a-zA-Z]\w*)*([|][a-zA-Z]\w*)?(?!\')(?=\W|$))')

    _filters = {}

    _FILTER_SEP = '|'

    def __init__(self, template_str=None,
                 template_fp=None,
                 template_file = '',
                 errors=False, default=None,
                 remove_indentation=True):
        """A General purpose Template renderer

            :param template_str: The Template to render
            :param errors: A Boolean flag - True if errors in the template should
                        cause an exception
            :param default: The default value to insert into the template if an error
                        occurs. If None the
        """
        if template_fp:
            template_str = template_fp.read()
        elif template_file:
            with open(template_file, 'r') as fp:
                template_str = fp.read()
        else:
            template_str = template_str if template_str else ''

        self._template_str = template_str

        if not self._template_str:
            six.raise_from(ValueError('Template cannot be blank/empty'), None)

        self._indent = 4
        self._extend = False
        self._source_parts = []
        self._source = None
        self._errors = errors

        self._errors = errors
        self._ignore_indentation = remove_indentation
        self._default = default
        self._render = self._compile()

    @classmethod
    def register_filter(cls, name, filter_callable):
        """Register a named modifier - internal use only"""
        cls._filters[name] = filter_callable

    @classmethod
    def execute_filter(cls, filter_name='', token='', value=None, args=(), kwargs={}):
        """Generic class method to execute a named filter

           Run at execute time
        """
        func = cls._filters[filter_name]
        try:
            return func(value, *args, **kwargs)
        except UnexpectedFilterArguments:
            six.raise_from(UnexpectedFilterArguments(
                "Unexpected filter arguments in \'{token}\'".format(
                    token=token, args=''.join(args), kwargs=' '.join(kwargs))), None)

    def _end_block(self, dedent=False):
        """Record the end of the block in the source code"""
        if self._extend:
            self._block_source.append('])\n')
        self._extend = False
        if dedent:
            self._indent -= 4

    def _start_block(self, indent=False):
        """Record the start of the block in the source code"""
        if indent:
            self._indent += 4

    def _compile_expression(self, expression_text):
        """Compile an expression

            Find all potential name within the expression (which might be filtered)
            and pass them to be compiled - filter out known keywords
            Pass the rest of the expression as is.
        """
        s = ''
        last_end = 0
        for match in self._variable_re.finditer(expression_text):
            to = match.start('Variable')
            s += expression_text[last_end:to]
            var = match.group('Variable')
            if var in ['in', 'is', 'not', 'True', 'False', 'and', 'or', 'xor',
                       'lambda']:
                s += var
            else:
                s += self._compile_filtered_token(var)
            last_end = match.end('Variable')
        else:
            s += expression_text[last_end:]
        return s

    def _compile_if(self, statement_token):
        """ Compile an If stateement

            Check that the if statement has a valid syntax
            Pass the expression to the expression compiler
            Start a new block
        """
        m = self._if_parse_re.match(statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Invalid if statement \'{{% {}\''.format(
                    statement_token)), None)
        expression = self._compile_expression(m.group('expression'))
        self._block_stack.append(('if', None))
        self._end_block()
        self._block_source.append(
            ' ' * self._indent + 'if {}'.format(expression) + ':\n')
        self._start_block(indent=True)

    def _compile_elif(self, statement_token):
        """ Compile an elif stateement

            Check that the elif statement has a valid syntax
            Pass the expression to the expression compiler
            Start a new block
        """
        try:
            start_block = self._block_stack.pop()
        except IndexError:
            start_block = ('','')

        if start_block[0] != 'if':
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{% elif %}\' outside an \'{% if %}\' block'),
                None)
        m = self._elif_parse_re.match(statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Invalid elif statement \'{{% {}\''.format(
                    statement_token)), None)
        expression = self._compile_expression(m.group('expression'))
        self._block_stack.append(('elif', None))
        self._end_block(dedent=True)
        self._block_source.append(
            ' ' * self._indent + 'elif {}'.format(expression) + ':\n')
        self._start_block(indent=True)

    def _compile_endif(self, token):
        """ Compile an endif stateement

            Check that an if statement exists.
            end the current block
        """
        try:
            start_block = self._block_stack.pop()
        except IndexError:
            start_block = ('','')

        if start_block[0] == 'if' or start_block[0] == 'elif':
            self._end_block(dedent=True)
        else:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% endif %}}\' outside an \'{{% if %}}\' block'.format(
                    token)), None)

    def _compile_else(self, token):
        """ Compile an else stateement

            Check that an if,elif or for statement exists.
            end the current block, start a new one.
        """
        try:
            last_block = self._block_stack.pop()
        except IndexError:
            last_block = ('','')

        if not last_block[0]:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% else %}}\' outside {{% if %}} or {{% for %}} block'.format(
                    token)), None)

        # Sanity check just incase
        if last_block[0]  in ['if', 'elif', 'for']:
            if last_block[1] == 'else':
                six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Unexpected directive - found \'{{% else %}}\' expected \'{{% endif %}}\''.format(
                        token)), None)

            self._end_block(dedent=True)
            self._block_source.append(' ' * self._indent + 'else' + ':\n')
            self._block_stack.append((last_block[0], 'else'))
            self._start_block(indent=True)

    def _compile_for(self, for_statement_token):
        """ Compile for statement

            Check the syntax of the for statement : for <targets> in <expression>

            Find all the targets and add them to the target set
            output the for statement
            start a new block
        """
        m = self._for_parse_re.match(for_statement_token)
        if not m:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Invalid for statement \'{{% {}\''.format(
                    for_statement_token)), None)

        targets = m.group('target').split(',')
        for target in targets:
            target = target.strip()
            if '.' in target or self._FILTER_SEP in target:
                six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Invalid target in for loop \'{}\''.format(
                        target)), None)
            self._targets.add(target)

        self._block_stack.append(('for', None))
        self._end_block()
        self._block_source.append(
            ' ' * self._indent + 'for {targets} in {iterable}:\n'.format(
                targets=m.group('target'),
                iterable=self._compile_expression(m.group('iterable'))))
        self._start_block(indent=True)

    def _compile_endfor(self, token):
        """Compile endfor statement

           Check current in a for block
           end the block
        """
        try:
            start_block = self._block_stack.pop()
        except IndexError:
            start_block = ('','')

        if start_block[0] == 'for':
            self._end_block(dedent=True)
        else:
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Unexpected directive - found \'{{% endfor %}}\' outside \'{{% for %}}\' block'.format(
                    token)), None)

    def _add_line(self, text, section_lines=None):
        section_lines = self._block_source if section_lines is None else section_lines

        if not self._extend:
            self._block_source.append(
                ' ' * self._indent + 'segment_extend([')
            self._extend = True

        self._block_source.append(text + ',')

    def _compile_token_stream(self, token_stream):
        """Compile the main chunk of the template
        """
        last_token_directive = False

        # Simple jump table - no locations but consistent names is important
        command_jmp_table = {'for','endfor','if','elif','else','endif'}

        # Container for the source of this section
        self._block_source = []

        # Mark the start of the block
        self._start_block()
        self._extend = False
        for token in token_stream:
            if not token:
                continue

            if token.startswith('{#'):
                last_token_directive = True
                continue

            if token.strip().startswith('{%'):
                last_token_directive = True
                inner_token = token.strip()[2:].strip()

                command = inner_token.split()[0]

                if command in command_jmp_table:
                    getattr(self, '_compile_'+command)(inner_token)
                    continue

                if inner_token[:-2].strip() in ['break', 'continue']:
                    if ('for', None) not in self._block_stack:
                        six.raise_from(TemplateSyntaxError(
                            'Syntax Error : Unexpected directive - found \'{token}\' outside \'{{% for %}}\' block'.format(
                                token=token)), None)
                    self._end_block()
                    self._block_source.append(' ' * self._indent + inner_token[:-2].strip() + '\n')
                    continue

                six.raise_from(TemplateSyntaxError(
                    'Syntax Error : Unexpected directive \'{{% {}\' found'.format(
                        inner_token)), None)

            if token.startswith('{{'):
                inner_token = token.strip()[2:-2].strip()
                value = 'str({})'.format(self._compile_filtered_token(token))
                self._add_line(value)

            else:
                # All '\n in must be preserved apart from the first one (after a directive)
                # All left indentation (after a \n) must be removed
                lines = token.splitlines(True)
                for line in lines:
                    if line == '\n' and last_token_directive:
                        last_token_directive = False
                        continue

                    token = line if not self._ignore_indentation else line.lstrip(' \t')

                    self._add_line(repr(token))

        if self._extend:
            self._block_source.append('])\n')

    def _compile(self):
        """Compile a template into an executable function

            Build a prolog of the function declaration, local variables

            Split the template into a stream and compile it
            add local variables to fetch the initial bits of the context
            add the compiled template source, and the return statement
        """

        indent = 4
        self._extend = False
        self._targets = set()
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

        self._compile_token_stream(tokens)

        if len(self._block_stack) != 0:
            last_token = self._block_stack.pop()
            six.raise_from(TemplateSyntaxError(
                'Syntax Error : Missing directive \'{{% end{} %}}\''.format(
                    last_token[0])), None)

        for local_var in self._locals:
            self._source_parts.append(
                ' ' * indent + '{var_name} = context.get({var_name!r},None)\n'.format(var_name=local_var))

        self._source_parts.extend(self._block_source)

        self._source_parts.append(
            ' ' * indent + 'return \'\'.join(segments)\n')

        self._source = ''.join(self._source_parts)
        globals_source = {}
        try:
            six.exec_(self._source, globals_source)
            return globals_source['render']
        except Exception as e:
            six.raise_from(e, None)

    def _compile_filtered_token(self, token):
        """Compile a context variable access with a filter

           Handles filter with and without args
        """
        variable = token.strip() if not token.startswith('{{') else token[2:-2].strip()
        if self._FILTER_SEP in variable:

            # Split toekn in contexxt variable and filter details
            dotted_name, filter_name = variable.split(self._FILTER_SEP)
            dotted_name, filter_name = dotted_name.rstrip(), filter_name.lstrip()

            # Split off any arguments - working from the first space
            if ' ' in filter_name:
                first_space = filter_name.find(' ')
                filter_name, args = filter_name[:first_space], filter_name[first_space + 1:]
            else:
                filter_name, args = filter_name, None

            pargs, kwargs = self._split_args(args) if args else ((), {})

            if filter_name not in self.__class__._filters:
                six.raise_from(
                UnrecognisedFilter('Unknown filter \'{}\''.format(filter_name)),
                None)
        else:
            filter_name = None
            dotted_name = variable
            pargs, kwargs = (), {}

        parts = [dotted_name] if '.' not in dotted_name else dotted_name.split('.')

        var = 'renderer._dodots(token={token!r}, value={value}, parts={parts!r} , context=context)'.format(
                    value=parts[0],
                    parts=parts[:],
                    token = token)

        if parts[0] not in self._targets:
            self._locals.add(parts[0])

        if filter_name is not None:
            return 'renderer.__class__.execute_filter( filter_name={filter_name!r},token={token!r},value={var},args={pargs!r}, kwargs={kwargs!r})'.format(
                cls_name=self.__class__.__name__,
                filter_name=filter_name,
                token=token,
                var=var,
                pargs=pargs,
                kwargs=kwargs)
        else:
            return var

        # Todo Extend for publicly defined filters ?

    def _dodots(self, token='', value=None, parts=None, context={}):
        """Process a expression - i.e. access to a data item within the context

           A wrapper around self._resolvedots so that errors are dealt with as
           requested by the caller

           Executed at run time only

           :param token: The full token for error reporting only - remove ??
           :param value: The actual value of the first/only part of the name
           :param parts: The separated parts of the dotted name - including the name of the value
           :param as_string: Whether this should return a string of a value - remove ??
           :param context:  The operational context for this template
        """
        as_string = token.startswith('{{')

        # If the first name isn't in the context and isn't in the targets wrap produce a 'default' value
        if parts[0] not in context and parts[0] not in self._targets:
            if self._errors:
                six.raise_from(UnknownContextValue('Unknown context variable \'{}\''.format(token)),None)
            else:
                return '' if not as_string else (self._default if self._default else token)

        # Try to resolve any further dotte dess
        current_value = value

        parts = parts[1:] if len(parts) > 1 else []

        for sub_item in parts:
            if isinstance(current_value, Mapping):
                try:
                    current_value = current_value[sub_item]
                    continue
                except KeyError:
                    if self._errors:
                        six.raise_from(UnknownContextValue('Unknown context variable \'{}\''.format(token)),None)
                    else:
                        return '' if not as_string else (self._default if self._default else token)

            if hasattr(current_value, sub_item):
                if callable(getattr(current_value, sub_item)):
                    current_value = getattr(current_value, sub_item)()
                    continue
                else:
                    current_value = getattr(current_value, sub_item)
                    continue
            else:
                if self._errors:
                    six.raise_from(UnknownContextValue('Unknown context variable \'{}\''.format(token)), None)
                else:
                    return '' if not as_string else (self._default if self._default else token)
        else:
            return current_value

    @classmethod
    def _split_args(self, args):
        """Helper method - Convert filter arguments into positional and keyword arguments

            Split filter arguments into positional and keyword arguments
        """
        matches = [m for m in Renderer._split_args_re.finditer(args)]
        p_args = tuple(
            [m.group('value').strip("\'") for m in matches if m.group('keyword') is None])
        kw_args = dict(
            [(m.group('keyword'), str(m.group('value').strip("\'"))) for m in matches if
             m.group('keyword') is not None])
        return p_args, kw_args

    def from_context(self, *contexts):
        """Public I/f Render the template based on one or more dictionaries"""

        this_context = {}
        for context in contexts:
            this_context.update(context)

        for var_name in self._locals:
            if var_name in this_context:
                continue

            if self._errors:
                raise UnknownContextValue('Unknown context variable \'{}\''.format(var_name))

        if not self._render:
            return None
        return self._render(self, this_context)

@registerModifier('len')
def variable_length(var, *args, **kwargs):
    """Returns a compiled call to len"""
    if args or kwargs:
        raise UnexpectedFilterArguments
    return len(var)

@registerModifier('split')
def variable_split(var, *args, **kwargs):
    """Returns a compiled call to capitalize"""
    if len(args) > 1 or kwargs:
        raise UnexpectedFilterArguments
    split_arg = (args[0],) if args else tuple()
    return str(var).split(*split_arg)


@registerModifier('cut')
def variable_cut(var, *args, **kwargs):
    """Returns a compiled call to the cut filter"""
    if 0 > len(args) > 1 or kwargs:
        raise UnexpectedFilterArguments
    return str(var).replace(args[0], '')

# To Do Test cut, implement center, date and other filters

# Todo Rework Filter system to allow registration of filters
