``testing.mysqld`` automatically setups a mysqld instance in a temporary directory, and destroys it after testing

.. image:: https://travis-ci.org/tk0miya/testing.mysqld.svg?branch=master
   :target: https://travis-ci.org/tk0miya/testing.mysqld

.. image:: https://coveralls.io/repos/tk0miya/testing.mysqld/badge.png?branch=master
   :target: https://coveralls.io/r/tk0miya/testing.mysqld?branch=master

.. image:: https://codeclimate.com/github/tk0miya/testing.mysqld/badges/gpa.svg
   :target: https://codeclimate.com/github/tk0miya/testing.mysqld

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


To make your tests faster
-------------------------

``testing.mysqld.Mysqld`` invokes ``initdb`` command on every instantiation.
That is very simple. But, in many cases, it is very waste that generating brandnew database for each testcase.

To optimize the behavior, use ``testing.mysqld.MysqldFactory``.
The factory class is able to cache the generated database beyond the testcases,
and it reduces the number of invocation of ``mysql_install_db`` command::

  import unittest
  import testing.mysqld

  # Generate Mysqld class which shares the generated database
  Mysqld = testing.mysqld.MysqldFactory(cache_initialized_db=True)


  def tearDownModule(self):
      # clear cached database at end of tests
      Mysqld.clear_cache()


  class MyTestCase(unittest.TestCase):
      def setUp(self):
          # Use the generated Mysqld class instead of testing.mysqld.Mysqld
          self.mysqld = Mysqld()

      def tearDown(self):
          self.mysqld.stop()

If you want to insert fixtures to the cached database, use ``initdb_handler`` option::

  # create initial data on create as fixtures into the database
  def handler(mysqld):
      conn = psycopg2.connect(**mysqld.dsn())
      cursor = conn.cursor()
      cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
      cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
      cursor.close()
      conn.commit()
      conn.close()

  # Use `handler()` on initialize database
  Mysqld = testing.mysqld.MysqldFactory(cache_initialized_db=True,
                                        on_initialized=handler)



Requirements
============
* Python 2.7, 3.3, 3.4, 3.5
* pymysql

License
=======
Apache License 2.0


History
=======

1.4.0 (2016-08-20)
-------------------
* Drop py26, py32 support
* Allow ``user`` and ``password`` argument to connect authorized database
* Depend on testing.common.database >= 2.0.0

1.3.0 (2016-02-03)
-------------------
* Add timeout to server invoker
* Support MySQL-5.7
* Add testing.mysqld.MysqldFactory
* Depend on ``testing.common.database`` package
* Assign port if networking not disabled

1.2.8 (2015-04-06)
-------------------
* Fix bugs

1.2.7 (2014-12-20)
-------------------
* Support for relative mysql_install_db links
* Use absolute path for which command

1.2.6 (2014-06-19)
-------------------
* Add timeout on terminating mysqld
* Fix bugs

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
