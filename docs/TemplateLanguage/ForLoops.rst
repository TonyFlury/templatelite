.. _ForLoops:

=========
For Loops
=========

Within templatelite, for loops have the following format:

.. code-block:: jinja

    {% for <targets> in <iterable> %}
        <Loop statements>
    {% endfor %}


``<targets>``
    a comma separated list of names (without dots) - just as in normal python each of these targets are created as local variables within the template, and can be accessed as if they are context variables.
``<iterable>``
    any :ref:`expression` which returns an iterable (as per usual python syntax). All names which are not quoted are assumed to be either local names created as the targets of other for loops, or context variables. These are full python syntax expression, including index and slicing, function calls and all mathematical and logical operators.See :ref:`expressions` for more details.
``<Loop statements>``
    Any combination of text, :ref:`ContextVariables`, other loops, and :ref:`IfConditionals`

Note that the ``{% endfor %}`` directive is mandatory.

Loops Inside a template can contain:

    - ``{% break %}`` which does the same as break in normal python - i.e. it immediately exist the containing loop.
    - ``{% continue %}`` which directives which have the same meanings as in usual for loops within Python - it moves execution to the start of the loop
    - ``{% else %}`` which will also behave in exactly the same way as in Python - the block after the {% else %} is only executed if the loop executes to the end - i.e. no {% break %} is executed.

With the else clause the full syntax is :

.. code-block:: jinja

    {% for <targets> in <iterable> %}
        <Loop statements>
    {% else %}
        <Else Statements>
    {% endfor %}

Loops can contain other loops, and there is no practical limit to the level of nesting that can be used.



