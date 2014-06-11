``testing.mysqld`` automatically setups a mysqld instance in a temporary directory, and destroys it after testing

.. image:: https://drone.io/bitbucket.org/tk0miya/testing.mysqld/status.png
   :target: https://drone.io/bitbucket.org/tk0miya/testing.mysqld
   :alt: drone.io CI build status

.. image:: https://pypip.in/v/testing.mysqld/badge.png
   :target: https://pypi.python.org/pypi/testing.mysqld/
   :alt: Latest PyPI version

.. image:: https://pypip.in/d/testing.mysqld/badge.png
   :target: https://pypi.python.org/pypi/testing.mysqld/
   :alt: Number of PyPI downloads

Install
=======
Use easy_install (or pip)::

   $ easy_install testing.mysqld

And ``testing.mysqld`` requires MySQL server in your PATH.


Usage
=====
Create MySQL instance using ``testing.mysqld.Mysqld``::

  import testing.mysqld
  from sqlalchemy import create_engine

  # Lanuch new MySQL server
  with testing.mysqld.Mysqld() as mysqld:
      # connect to MySQL
      engine = create_engine(mysqld.url())

      # if you use mysqldb or other drivers:
      #   import _mysql
      #   db = _mysql.connect(**mysqld.dsn())

      #
      # do any tests using MySQL...
      #

  # MySQL server is terminated here


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

      def tearDown(self):
          self.mysqld.stop()


Requirements
============
* Python 2.6, 2.7, 3.2, 3.3, 3.4
* pymysql

License
=======
Apache License 2.0


History
=======

1.2.5 (2014-06-11)
-------------------
* Fix ImportError if caught SIGINT on py3

1.2.4 (2014-02-13)
-------------------
* Fix testing.mysqld.Mysqld#start() fails if mysql_install_db does not create database named "test"

1.2.3 (2013-12-11)
-------------------
* Use pymysql driver as default in Mysqld#url()

1.2.2 (2013-12-06)
-------------------
* Change behavior: Mysqld#stop() cleans workdir
* Fix caught AttributeError on object deletion

1.2.1 (2013-12-05)
-------------------
* Add mysqld.skipIfNotInstalled decorator (alias of skipIfNotFound)
* Suport python 2.6 and 3.2

1.2.0 (2013-12-04)
-------------------
* Add @skipIfNotFound decorator

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
