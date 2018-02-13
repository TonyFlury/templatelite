.. _ContextVariables:

=================
Context Variables
=================

As the name suggests, ContextVariables are the method whereby templates can access data within the 'context'; the context is the dictionary passed to the Renderer class in the 'from_context' or `from_json` methods.

In it's simplest form a Context Variable is a single name, which will be a key within the context data; for instance ``name`` within a template will look for the key of ``name`` with the context.

.. _dotted_name:

dotted names
------------

As well as single names, templatelite supports dotted names - which allow deeper access to the data within the context. It is neccessary to distinguish between displayed data access - i.e. those with `{{` `}}`, and dotted names with are used in :ref: ``ForLoops`` and :ref:``If Statements<IfConditionals>``

.. _displayed data:

displayed data
##############

Within displayed data, an example dotted name of ``person.name`` variable will mean one of three things :

  - If the ``person`` key within the context is a dictionary (or any object which suports a Mapping type interface, then ``person.name`` in the template is equivalent to python code:  ``person['name']``
  - if ``person`` key within the context is an object which has a ``name`` method, then ``person.name`` in the template will be equivalent to ``person.name()`` - there is no capability within displayed context variables (i.e. those enclosed in `{{` `}}` within dotted names to pass parameters to these methods - but see :ref:``filters``.
  - if ``person`` key within the context is an object which has a ``name`` attribute, then ``person.name`` in the template will be equivalent to ``person.name``.

These dotted names can be nested as deep as required; there is no reason why a context variable of for instance : ``company.client.recent_order.value`` shouldn't actually be translated to the equivalent of context.client['recent_order'].value()

.. _expressions:

Expressions
###########

Within :ref:``For Loop<ForLoops>`` or :ref:``If Statement<IfConditional>`` then as well the tempalite dotted name extensions above, normal python syntax for data access can be used; for instance:

  - access by numeric index or slicing using ``container[index|slice]``: here container will be a valid :ref:``dotted name<dotted_name>`` as above, and index/slice can either be a literal numeric value, or be another :ref:``dotted name<dotted_name>``
  - access to keys in dictionaries using ``container[key]`` where container is a dotted name and key can be a literal name, or another dotted name,
  - calling methods and using paramaters using ``object.method_name(parameters)`` so long as the parameters are either positional, and any keyword arguments are passed by unpacking a dictionary (i.e. using the **) operator. All unquoted text is interpreted as a name within the context, and therefore errors are going to happen (either those keywords will be found within the context and replaced with data from the context, or the name won't be found in the context and an error will occurr).

.. _filters:

Filters
-------

Filters can be applied at the end of dotted names (wether in :ref:``displayed data``, or :ref:``expressions``) by using a '|' (vertical bar), and there are several builtin filters. Filters must be the last part of a context variable whether that is in a `{{` `}}` directive or in an expression.

See :ref:``filters`` for a full list of filters.

String filters
##############

    len
        Returns the length of the context variable - equivalent to len(<variable>)
        ``{{ var|len }}`` : is equivalent to len(var)


    split
        Splits the contex variable into a list. As a default this splits the value at each space character, equivalent to <variable>.split()
        Takes one optional argument which is the character to split on.
        ``{{var|split 'x'}}`` : is equivalent to var.split('x')


