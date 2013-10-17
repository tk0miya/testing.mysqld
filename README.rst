``test.mysqld`` automatically setups a mysqld instance in a temporary directory, and destroys it after testing

Install
=======
Use easy_install (or pip)::

   $ easy_install test.mysqld

And ``test.mysqld`` requires MySQL server in your PATH.


Usage
=====
Create MySQL instance using ``test.mysqld.Mysqld``::

  import test.mysqld
  mysqld = test.mysqld.Mysqld()  # Lanuch new MySQL server

  import _mysql
  db = _mysql.connect(**mysqld.dsn())
  #
  # do any tests using MySQL...
  #

  del mysqld                     # Terminate MySQL server


``test.mysqld.Mysqld`` executes ``mysql_install_db`` and ``mysqld`` on instantiation.
On deleteing Mysqld object, it terminates MySQL instance and removes temporary directory.

If you want database includes tables and any fixtures for your apps,
use ``copy_data_from`` keyword::

  # uses a copy of specified data directory of MySQL.
  mysqld = test.mysqld.Mysqld(copy_data_from='/path/to/your/database')


You can specify parameters for MySQL with ``my_cnf`` keyword::

  # boot MySQL server without socket listener (use unix-domain socket) 
  mysqld = test.mysqld.Mysqld(my_cnf={'skip-networking': None})


For example, you can setup new MySQL server for each testcases on setUp() method::

  import unittest
  import test.mysqld

  class MyTestCase(unittest.TestCase):
      def setUp(self):
          self.mysqld = test.mysqld.Mysqld(my_cnf={'skip-networking': None})


Requirements
============
* Python 2.7, 3.3

License
=======
Apache License 2.0


History
=======

1.0.0 (2013-10-16)
-------------------
* First release
