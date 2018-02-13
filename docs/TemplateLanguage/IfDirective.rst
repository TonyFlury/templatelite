.. _IfConditionals:

=============
If Conditions
=============

within tempalite, a template can have conditional sections by using the an ``if`` directive:

.. code-block:: jinja

    {% if <conditional> %}
        <statements>
    {% elif <conditional> %}
        <statements>
    {% else %}
        <statements>
    {% endif %}


``<conditional>``
    Any valid :ref:`expression` which generates a boolean value - just as in usual Python if statements

``<statements>``
    Any combination of text, :ref:`ContextVariables`, other loops, and :ref:`IfConditionals`

The ``{% elif <conditional> %}`` and ``{% else %}`` directives are entirely optional (as they are in Python), but the ``{% endif %}`` statement is mandatory. Unlike normal python code indentation of the directives is not required (but is good practice in order to illustrate the structure of the template.
