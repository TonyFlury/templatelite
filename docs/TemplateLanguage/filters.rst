.. _filters:

=======
Filters
=======

String filters
--------------

    center
        Centers the variable into a space, with an optional fill character

        ``{{ var|center 20 }}`` : is equivalent to var.center(20)
        ``{{ var|center 20 '#'}}`` : is equivalent to var.center(20,'#')

    cut
        Removes all of a given character from the string

        ``{{ var|cut 'x' }}`` : is equivalent to var.

    len
        Returns the length of the context variable - equivalent to len(<variable>)

        ``{{ var|len }}`` : is equivalent to len(var)


    split
        Splits the contex variable into a list. As a default this splits the value at each space character, equivalent to <variable>.split()
        Takes one optional argument which is the character to split on.

        ``{{var|split 'x' }}`` : is equivalent to var.split('x')

        ``{{var|split 'x' 5 }}`` : is equivalent to var.split('x', 5)

