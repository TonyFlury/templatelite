#! /usr/bin/env python
# coding=utf-8
"""
# templatelite : Lightweight Templating system

Summary :
    A very lightweight templatelite system - suitable for simple html and python code
Use Case :
    I want a simple to use templatelite system so that I can easily create text & html

Testable Statements :
    ...
"""
import sys
import unittest
import re
import click
import inspect
import six

import templatelite

class OrderedTestSuite(unittest.TestSuite):
    def __iter__(self):
        return iter(sorted(self._tests, key=lambda x:str(x)))


class SimpleTextAndComments(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_000_001_instatiation(self):
        """instantiate a Rendered instance"""
        renderer = templatelite.Renderer(template_str='b')
        self.assertIsInstance(renderer, templatelite.Renderer)

    def test_000_002_no_text(self):
        """Empty Template creates empty results"""
        with self.assertRaises(ValueError):
            renderer = templatelite.Renderer()

    def test_000_003_comment_only(self):
        """Single comment is ignored"""
        renderer = templatelite.Renderer('{# This should be ignored #}')
        self.assertEqual( renderer.from_context({}), '')

    def test_000_004_comments_embedded_in_text_only(self):
        """Text with embedded comments"""
        template =\
"""This is text {# with an embedded comment #}
and this is mo{# no whitespace inserted #}re text
{#Final comment #}This is it."""
        renderer = templatelite.Renderer(template)
        self.assertEqual( renderer.from_context(),
"""This is text and this is more text
This is it.""" )


class Substitutions(unittest.TestCase):

    def test_010_001_SimpleContext(self):
        """Simple template with a simple context"""
        template = 'My name is {{ name }}'
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'name':'Tony Flury'})
        self.assertEqual( result, 'My name is Tony Flury')

    def test_010_002_SimpleContextWithExtaWhiteSpace(self):
        """Simple template with extra white space around context name"""
        template = 'My name is {{      name       }}'
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'name':'Tony Flury'})
        self.assertEqual( result, 'My name is Tony Flury')

    def test_010_033_MissingContextValue(self):
        """Missing context data - default value"""
        template = 'My name is {{name}}'
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'me':'Tony Flury'})
        self.assertEqual( result, 'My name is {{name}}')

    def test_010_033_MissingContextValueError(self):
        """Missing context data - error raised"""
        template = 'My name is {{name}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        with six.assertRaisesRegex(self,
                                   templatelite.UnknownContextValue,
                                    r'Unknown context variable \'name\''):
            renderer.from_context( {'me': 'Tony Flury'})

    def test_010_034_MissingContextValueDefault(self):
        """Missing context data - error raised"""
        template = 'My name is {{name}}'
        renderer = templatelite.Renderer(template_str=template, default='!!Error!!')
        result = renderer.from_context({'me': 'Tony Flury'})
        self.assertEqual( result, 'My name is !!Error!!')

    def test_010_040_DottedNameDictionary(self):
        """Context variable is a dictionary with a dotted name in template"""
        template = 'My name is {{person.name}}'
        renderer = templatelite.Renderer(template_str=template,
                                        default='!!Error!!')
        result = renderer.from_context({'person':{'name': 'Tony Flury','age':53}})
        self.assertEqual( result, 'My name is Tony Flury')

    def test_010_041_DottedNameAttribute(self):
        """Context variable is an object with a dotted attribute name in template"""
        c = type('person',(object,),{'name':'Tony','age':53})()

        template = 'My name is {{person.name}}'
        renderer = templatelite.Renderer(template_str=template,
                                        default='!!Error!!')
        result = renderer.from_context({'person':c})
        self.assertEqual( result, 'My name is Tony')

    def test_010_041_DottedNameCallable(self):
        """Context variable is a object with a callable name in template"""
        template = 'My name is {{person.__len__}}'
        renderer = templatelite.Renderer(template_str=template,
                                        default='!!Error!!')
        result = renderer.from_context({'person':'Tony'})
        self.assertEqual( result, 'My name is 4')

    def test_010_050_DottedNameDictionaryMissingKeyDefaultValue(self):
        """Context variable is a dictionary with a with a missing key replaced by the default value"""
        template = 'My name is {{person.name}}'
        renderer = templatelite.Renderer(template_str=template,
                                        default='!!Error!!')
        result = renderer.from_context({'person':{'full-name': 'Tony Flury','age':53}})
        self.assertEqual( result, 'My name is !!Error!!')

    def test_010_051_DottedNameDictionaryMissingKeyNoDefault(self):
        """Context variable is a dictionary with a with a missing key replace by token"""
        template = 'My name is {{person.name}}'
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'person':{'full-name': 'Tony Flury','age':53}})
        self.assertEqual( result, 'My name is {{person.name}}')

    def test_010_052_DottedNameDictionaryMissingKeyError(self):
        """Context variable is a dictionary with a with a missing key raises Exception"""
        template = 'My name is {{person.name}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        with six.assertRaisesRegex(self,
                                   templatelite.UnknownContextValue,
                                    r'Unknown context variable \'{{person.name}}\''):
            result = renderer.from_context({'person':{'full-name': 'Tony Flury','age':53}})


class Filters(unittest.TestCase):
    def test_020_001_unknown_filter(self):
        """Test that an unknown filter raises an error"""
        template = 'My name is {{person.name|blah}}'
        with six.assertRaisesRegex(self, templatelite.UnrecognisedFilter, r'Unknown filter \'blah\''):
            renderer = templatelite.Renderer(template_str=template, errors=True)

    def test_020_002_length_filter(self):
        """Test the Length filter"""
        template = 'My name is {{person.name|len}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        result = renderer.from_context({'person':{'name': 'Tony Flury','age':53}})
        self.assertEqual( result, 'My name is 10')

    def test_020_002e_length_filter_with_args(self):
        """Test the Length filter with arguments (in error)"""
        template = 'My name is {{person.name|len 193}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        with six.assertRaisesRegex(self, templatelite.UnexpectedFilterArguments, r"Unexpected filter arguments in '{{person.name|len 193}}'"):
            result = renderer.from_context({'person':{'name':'Tony'}})

    def test_020_010_split_filter(self):
        """Test the split filter with default"""
        template = 'My name is {{person.name|split}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        result = renderer.from_context({'person':{'name': 'tony flury','age':53}})
        self.assertEqual(result, 'My name is [\'tony\', \'flury\']')

    def test_020_011_split_filter_argument(self):
        """Test the split filter with argument"""
        template = 'My name is {{v|split e}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        result = renderer.from_context({'v':'1e2e3e4e5e6e7e8e9e0'})
        self.assertEqual( result, "My name is ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']" )

    def test_020_012_split_filter_error(self):
        """Test the capitalise filter with default"""
        template = 'My name is {{v|split e b}}'
        renderer = templatelite.Renderer(template_str=template, errors=True)
        with six.assertRaisesRegex(self, templatelite.UnexpectedFilterArguments, r"Unexpected filter arguments in \'{{v|split e b}}\'"):
            renderer.from_context({'v':'Hello'})

class IfStatement(unittest.TestCase):
    def test_030_000_invalid_if_missing_expression(self):
        """Invalid if statement - missing an expression"""
        template = """{% if %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Invalid if statement \'\{% if %\}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_001_invalid_if_missing_endif(self):
        """Invalid template missing endif"""
        template = """{% if True %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Missing directive \'{% endif %}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_002_invalid_lone_else(self):
        """Invalid template - else without and if or for"""
        template = """{% else %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Unexpected directive - found \'{% else %}\' outside {% if %} or {% for %} block"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_003_invalid_lone_else(self):
        """Invalid template - else after another else"""
        template = """{% if True %}
Hello
{% else %}
Goodbye
{% else %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Unexpected directive - found \'{% else %}\' expected \'{% endif %}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_004_invalid_lone_elif(self):
        """Invalid template - elif without a starting if"""
        template = """{% elif True %}
        {% endif %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError,
                                   r"Syntax Error : Unexpected directive - found \'{% elif %}\' outside an \'{% if %}\' block"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_005_invalid_elif(self):
        """Invalid template - elif without an expression"""
        template = """{% if True %}
        {% elif %}
        {% endif %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError,
                                   r"Syntax Error : Invalid elif statement \'{% elif %}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_006_invalid_if_expression(self):
        """Invalid expression - Syntax Error"""
        template = """{% if True+ %}
        {% endif %}"""
        with self.assertRaises(SyntaxError):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_005_invalid_endif(self):
        """Invalid template - endif without if statement"""
        template = """{% endif %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError,
                                   r"Syntax Error : Unexpected directive - found \'{% endif %}\' outside an \'{% if %}\' block"):
            renderer = templatelite.Renderer(template_str=template)

    def test_030_010_valid_if_endif(self):
        """Valid template - if with endif"""
        template = """{% if dummy %}
        Hello
        {% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'dummy': False})
        self.assertEqual(result, '')

    def test_030_011_valid_with_else(self):
        """Valid template - if else endif"""
        template = """{% if dummy %}
Hello
{% else %}
Goodbye
{% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'dummy':True})
        self.assertEqual( result, 'Hello\n')
        result = renderer.from_context({'dummy':False})
        self.assertEqual( result, 'Goodbye\n')

    def test_030_012_valid_with_elif(self):
        """Valid template - if elif endif"""
        template = """{% if dummy==1 %}
Hello
{% elif dummy==2 %}
Goodbye
{% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        result = renderer.from_context({'dummy':1})
        self.assertEqual( result, 'Hello\n')
        result = renderer.from_context({'dummy':2})
        self.assertEqual( result, 'Goodbye\n')

    def test_030_013_elif_with_else(self):
        """Valid template - if elif else endif"""
        template = """{% if dummy==1 %}
Hello
{% elif dummy==2 %}
Goodbye
{% else %}
Au Revoir
{% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual( renderer.from_context({'dummy':1}), 'Hello\n')
        self.assertEqual(renderer.from_context({'dummy':2}),'Goodbye\n')
        self.assertEqual(renderer.from_context({'dummy':3}),'Au Revoir\n')

    def test_030_015_if_on_one_line(self):
        """Valid template - if elif else endif"""
        template = "{% if dummy==1 %} Hello {% elif dummy==2 %} Goodbye {% else %} Au Revoir {% endif %}"
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual(renderer.from_context({'dummy': 1}), 'Hello')
        self.assertEqual(renderer.from_context({'dummy': 2}), 'Goodbye')
        self.assertEqual(renderer.from_context({'dummy': 3}), 'Au Revoir')

    def test_030_020_if_with_in(self):
        """Valid template - if with an 'in' test - ensure neither in or quoted strings are 'compiled' """
        template = """{% if data in ['a','b','c'] %}
        Hello
        {% elif data in ['d','e','f'] %}
        Goodbye
        {% else %}
        Au Revoir
        {% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual(renderer.from_context({'data':'a'}),'Hello\n')
        self.assertEqual(renderer.from_context({'data':'b'}),'Hello\n')
        self.assertEqual(renderer.from_context({'data':'c'}),'Hello\n')
        self.assertEqual(renderer.from_context({'data':'d'}),'Goodbye\n')
        self.assertEqual(renderer.from_context({'data':'e'}),'Goodbye\n')
        self.assertEqual(renderer.from_context({'data':'f'}),'Goodbye\n')
        self.assertEqual(renderer.from_context({'data':'other'}),'Au Revoir\n')

    def test_030_030_expression_substitution_index(self):
        """Valid template - with compiled names within indexes """
        template = """{% if data[key1] == data[key2] %}
        The same
        {% else %}
        Different
        {% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual(renderer.from_context({'data':[1,2,3,3,4],'key1':2,'key2':3}),'The same\n')
        self.assertEqual(renderer.from_context({'data':[1,2,3,3,4],'key1':0,'key2':1}),'Different\n')

    def test_030_035_expression_substitution_key(self):
        """Valid template - with compiled names as dictionary keys """
        template = """{% if data[key1] == data[key2] %}
        The same
        {% else %}
        Different
        {% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual(renderer.from_context({'data':{1:1,2:2,3:3,4:3,5:4},'key1':3,'key2':4}),'The same\n')
        self.assertEqual(renderer.from_context({'data':{1:1,2:2,3:3,4:3,5:4},'key1':1,'key2':5}),'Different\n')

    def test_030_037_expression_functioncall(self):
        """Valid template - with explicit function call - with parameters """
        def func(n):
            return 0 if n >5  else 1

        template = """{% if data(key1) == data(key2) %}
        The same
        {% else %}
        Different
        {% endif %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual(renderer.from_context({'data':func,'key1':7,'key2':8}),'The same\n')
        self.assertEqual(renderer.from_context({'data':func,'key1':1,'key2':8}),'Different\n')


class ForLoop(unittest.TestCase):
    def test_040_000_invalid_for_loop_missing_itervar(self):
        """Invalid for loop - missing targets and iterable"""
        template = '{% for %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Invalid for statement \'\{% for %\}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_001_invalid_for_loop_missing_iterator(self):
        """Invalid for loop - missing iterable"""
        template = '{% for plip in %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Invalid for statement \'\{% for plip in %\}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_002_invalid_for_loop_invalid_single_target(self):
        """Invalid for loop - invalid target"""
        template = '{% for plip.x in dummy%}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Invalid target in for loop \'plip.x\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_003_invalid_for_loop_invalid_multple_target(self):
        """Invalid for loop - one invalid target"""
        template = '{% for z, plip.x in dummy%}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Invalid target in for loop \'plip.x\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_004_invalid_for_loop_missing_end_for(self):
        """Invalid for loop - missing endfor"""
        template = '{% for z, plip in dummy %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Missing directive \'{% endfor %}\'"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_005_break_outside_loop(self):
        """Invalid for loop - break outside a loop"""
        template = '{% break %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Unexpected directive - found \'{% break %}\' outside \'{% for %}\' block"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_006_continue_outside_loop(self):
        """Invalid for loop - continue outside a loop"""
        template = '{% continue %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Unexpected directive - found \'{% continue %}\' outside \'{% for %}\' block"):
            renderer = templatelite.Renderer(template_str=template)

    def test_040_006_endfor_outside_loop(self):
        """Invalid for loop - endfor outside a loop"""
        template = '{% endfor %}'
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r"Syntax Error : Unexpected directive - found \'{% endfor %}\' outside \'{% for %}\' block"):
            renderer = templatelite.Renderer(template_str=template)


    def test_040_010_syntax_check_for_loop(self):
        """Prove that for loop completes syntax check"""
        template =\
"""{% for z, plip in dummy%}
    block
{% endfor %}
outer block
"""
        renderer = templatelite.Renderer(template_str=template)

    def test_040_011_simple_for(self):
        """Simple For loop"""
        template =\
"""FirstLine
{% for n in dummy%}
        {{ n }}
{% endfor %}
outer block
"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=False)
        result = renderer.from_context({'dummy': [1,2,3,4,5]})
        self.assertEqual(result,
"""FirstLine
        1
        2
        3
        4
        5
outer block
""")

    def test_040_020_for_with_break(self):
        """For loop with a break"""
        template = \
    """FirstLine
    {% for n in dummy%}
        {% if n ==3 %}
            {% break %}
        {% endif %}
            {{ n }}
    {% endfor %}
    outer block"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=False)
        result = renderer.from_context({'dummy': [1,2,3,4,5]})
        self.assertEqual(result,
"""FirstLine
            1
            2
    outer block""")

    def test_040_021_for_with_continue(self):
        """For loop with a continue"""
        template = \
            """{% for n in dummy%}
                {% if n ==3 %}
                    {% continue %}
                {% endif %}
{{ n }}
                {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=False)
        self.assertEqual( renderer.from_context({'dummy': [1,2,3,4,5]}).strip(), '1\n2\n4\n5')

    def test_040_022_for_with_else(self):
        """For loop with a else"""
        template = \
            """{% for n in dummy%}
                {% if n ==3 %}
                    {% break %}
                {% endif %}
            {% else %}
            Not Found !
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=False)
        self.assertEqual( renderer.from_context({'dummy': [1,2,3,4,5]}).strip(), '')
        self.assertEqual( renderer.from_context({'dummy': [1,2,4,5]}).strip(), 'Not Found !')

    def test_040_030_filter_on_for_loop_target(self):
        """For looop - filter used on loop target variable"""
        template = """{% for n in dummy%}
        {{ n|len }}
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=True)
        self.assertEqual( renderer.from_context({'dummy': ['','1','22','333','4444']}).strip(), '0\n1\n2\n3\n4')

    def test_040_031_for_loop_target(self):
        """For looop - filter used on loop target variable"""
        template = """{% for n in dummy%}
        {{ n }}
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=True)
        self.assertEqual( renderer.from_context({'dummy': ['0','1','2','3','4']}).strip(), '0\n1\n2\n3\n4')

    def test_040_031_for_loop_indentation_intact(self):
        """For looop - filter used on loop target variable"""
        template = """{% for n in dummy%}
    {{ n }}
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template, remove_indentation=False)
        self.assertEqual( renderer.from_context({'dummy': ['0','1','2','3','4']}), '    0\n    1\n    2\n    3\n    4\n')

    def test_040_032_multiple_for_loop_target(self):
        """For looop - filter used on loop target variable"""
        template = """{% for n,r in dummy%}
        {{ n }} : {{ r }}
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template)
        self.assertEqual( renderer.from_context({'dummy': zip([0,1,2,3,4],['a','b','c','d','e'])}).strip(), '0: a\n1: b\n2: c\n3: d\n4: e')

    def test_040_040_for_loop_variable_error(self):
        """For looop - error fetching iterator"""
        template = """{% for n in doesnt_exist %}
inside loop
            {% endfor %}"""
        renderer = templatelite.Renderer(template_str=template,
                                         remove_indentation=True)
        self.assertEqual( renderer.from_context({}).strip(),'')

    def test_040_045_for_loop_variable_singleline(self):
        """For loop - for loop on a single line"""
        template = "{% for n in l %} {{ n }} {% endfor %}"
        renderer = templatelite.Renderer(template_str=template,
                                         remove_indentation=True)
        self.assertEqual( renderer.from_context({'l':[0,1,2,3,4,5,6]}).strip(), '0123456')

class ErrorConditions(unittest.TestCase):

    def test_100_000_invalid_directive(self):
        """Invalid Template - unknown directive token"""
        template = """{% frooble %}"""
        with six.assertRaisesRegex(self, templatelite.TemplateSyntaxError, r'Syntax Error : Unexpected directive \'{% frooble %}\' found'):
            renderer = templatelite.Renderer(template_str=template)

# noinspection PyMissingOrEmptyDocstring,PyUnusedLocal
def load_tests(loader, tests=None, patterns=None,excludes=None):
    """Load tests from all of the relevant classes, and order them"""
    classes = [cls for name, cls in inspect.getmembers(sys.modules[__name__],
                                                       inspect.isclass)
               if issubclass(cls, unittest.TestCase)]

    suite = OrderedTestSuite()
    for test_class in classes:
        tests = loader.loadTestsFromTestCase(test_class)
        if patterns:
            tests = [test for test in tests if all(re.search(pattern, test.id()) for pattern in patterns)]
        if excludes:
            tests = [test for test in tests if not any(re.search(exclude_pattern,test.id()) for exclude_pattern in excludes)]
        suite.addTests(tests)
    return suite

@click.command()
@click.option('-v', '--verbose', default=2, help='Level of output', count=True)
@click.option('-s', '--silent', is_flag=True, default=False, help='Supress all output apart from a summary line of dots and test count')
@click.option('-x', '--exclude', metavar='EXCLUDE', multiple=True, help='Exclude where the names contain the [EXCLUDE] pattern')
@click.argument('patterns', nargs=-1, required=False, type=str)
def main(verbose, silent, patterns, exclude):
    """Execute the unit test cases where the test id match the patterns

    Test cases are only included for execution if their names (the class name and the method name)
    contain any of the text in any of the [PATTERNS].
    Test cases are excluded from execution if their names contain any of the text in any of the [EXCLUSION]
    patterns

    Both [PATTERNS] and [EXCLUSION] can be regular expressions (using the re syntax)

    \b
    A single -v produces a single '.' for each test executed
    Using -v -v produces an output of the method name and 1st line of any
            doc string for each test executed
    """
    verbose = 0 if silent else verbose

    ldr = unittest.TestLoader()
    test_suite = load_tests(ldr, patterns=patterns, excludes=exclude)
    unittest.TextTestRunner(verbosity=verbose).run(test_suite)

if __name__ == '__main__':
    main()