============
Introduction
============

Templatelite is a lightweight templating module which is specifically designed to enable code creation as well as creation of other forms of data.

The templates are based on jinja templating language with a the exception that templalite does not support blocks, and does not support template extending; i.e. the ability for one template to override one or more blocks in another template.

templatelite supports a python like language within the template :

   - for loops with multiple target variables, and supporting break and continue and else
   - if conditional with elif and else

In general the templating process works as follows :

    - Create an instance of the Renderer class, using your template either from a string or a file
    - Use one of the methods of the class to add data to the template, the data can be created from a dictionary, multiple key word arguments or json data. The process of adding data to the template is termed ``rendering``, and the data used to render the template is called the context

Access to Data
==============

Within the templating language there is support for the display of data from  the conex, using ``Context Variables`` (i.e. variable names surrounded by `{{` & `}}` (as in the example below).

.. code-block:: jinja

    {{ name }}

When this template is rendered using a dictionary with a key of `name`, the output will be the template with `{{ name }}` replaced with the value in the dictionary for that key. See :ref:`ContextVariables` for more details.

Control Structures
==================
As well as accessing data from the context the templating language supports simple looping, and conditional branching through template directives; Python like commands surrounded by `{%` & `%}` as in the examples below.

Loops
-----

Tempalite supports for loops which allow for iteration around context data :

.. code-block:: jinja

    {% for person in people %}
        {{ person }}
    {% endfor %}

For full details of the for loop see :ref:`ForLoops`. The templatelite module does not have while loops.


Conditional Branching
---------------------

Tempalite supports if statements so that your template can implement 'decisions' based on data.

.. code-block:: jinja

    {% if person == 'Elizabeth Windsor'  %}
         Her Majest Queen Elizabeth
    {% else %}
        A commoner
    {% endif %}

For full details of the if directive see :ref:`IfConditionals`.

Comments
========

Comments can be added to templates by surrounded your comment by `{#` & `#}`. In complex templates these comments can be useful in understanding your own templates. They are ignored entirely :

.. code-block:: jinja

 This is a {# This is a comment #}message

Will be rendered as :

    This is a message


