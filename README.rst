pvr
===

.. note::
    This project is nothing more than a proof of concept at this point in time,
    it only actually works with the ``venv`` module and Python 3.

pvr is a virtual environment management utility for Python. It uses either the
``venv`` module or ``virtualenv`` to supply the underlying isolation while
providing a better UX on top of those.


Usage
-----

.. code-block:: console

    $ # Create a named environment
    $ pvr create myenv
    $ # Execute a command within a named environment
    $ pvr exec myenv pip install requests
    $ # Remove a named environment
    $ pvr remove myenv
