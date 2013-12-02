``testing.mysqld`` automatically setups a mysqld instance in a temporary directory, and destroys it after testing

Install
=======
Use easy_install (or pip)::

   $ easy_install testing.mysqld

And ``testing.mysqld`` requires MySQL server in your PATH.


Usage
=====
Create MySQL instance using ``testing.mysqld.Mysqld``::

  import testing.mysqld
  mysqld = testing.mysqld.Mysqld()  # Lanuch new MySQL server

  # connect to MySQL
  from sqlalchemy import create_engine
  engine = create_engine(mysqld.url())

  # if you use mysqldb or other drivers:
  #   import _mysql
  #   db = _mysql.connect(**mysqld.dsn())

  #
  # do any tests using MySQL...
  #

  del mysqld                     # Terminate MySQL server


``testing.mysqld.Mysqld`` executes ``mysql_install_db`` and ``mysqld`` on instantiation.
On deleting Mysqld object, it terminates MySQL instance and removes temporary directory.

If you want a database including tables and any fixtures for your apps,
use ``copy_data_from`` keyword::

  # uses a copy of specified data directory of MySQL.
  mysqld = testing.mysqld.Mysqld(copy_data_from='/path/to/your/database')


You can specify parameters for MySQL with ``my_cnf`` keyword::

  # boot MySQL server without socket listener (use unix-domain socket) 
  mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})


For example, you can setup new MySQL server for each testcases on setUp() method::

  import unittest
  import testing.mysqld

  class MyTestCase(unittest.TestCase):
      def setUp(self):
          self.mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})


Requirements
============
* Python 2.7, 3.3
* pymysql

License
=======
Apache License 2.0


History
=======

1.1.2 (2013-11-26)
-------------------
* Fix it does not cleanup temporary directory if Mysqld object has been deleted

1.1.1 (2013-11-25)
-------------------
* Add charset parameter to Mysqld#url()

1.1.0 (2013-11-22)
-------------------
* Rename package: test.mysqld -> testing.mysqld
* Add Mysqld#url() method (for sqlalchemy)

1.0.0 (2013-10-17)
-------------------
* First release
