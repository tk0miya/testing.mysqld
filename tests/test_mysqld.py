# -*- coding: utf-8 -*-

import os
import sys
import signal
import tempfile
import testing.mysqld
from mock import patch
from time import sleep
from shutil import rmtree
from contextlib import closing
import pymysql
import sqlalchemy

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestMysqld(unittest.TestCase):
    def test_basic(self):
        try:
            # start mysql server
            mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
            self.assertIsNotNone(mysqld)
            self.assertEqual(mysqld.dsn(),
                             dict(unix_socket=mysqld.base_dir + '/tmp/mysql.sock',
                                  user='root',
                                  db='test'))

            # connect to mysql (w/ pymysql)
            conn = pymysql.connect(**mysqld.dsn())
            self.assertIsNotNone(conn)
            self.assertRegexpMatches(mysqld.read_bootlog(), 'ready for connections')

            # connect to mysql (w/ sqlalchemy)
            engine = sqlalchemy.create_engine(mysqld.url())
            self.assertIsNotNone(engine)

            # shutting down
            pid = mysqld.server_pid
            self.assertTrue(os.path.exists(mysqld.base_dir + '/tmp/mysql.sock'))
            self.assertTrue(mysqld.is_alive())
        finally:
            mysqld.stop()
            sleep(1)

            self.assertFalse(os.path.exists(mysqld.base_dir + '/tmp/mysql.sock'))
            self.assertFalse(mysqld.is_alive())
            with self.assertRaises(OSError):
                os.kill(pid, 0)  # process is down

    def test_stop(self):
        # start mysql server
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        self.assertTrue(os.path.exists(mysqld.base_dir))
        self.assertTrue(mysqld.is_alive())

        # call stop()
        mysqld.stop()
        self.assertFalse(os.path.exists(mysqld.base_dir))
        self.assertFalse(mysqld.is_alive())

        # call stop() again
        mysqld.stop()
        self.assertFalse(os.path.exists(mysqld.base_dir))
        self.assertFalse(mysqld.is_alive())

        # delete mysqld object after stop()
        del mysqld

    def test_dsn_and_url(self):
        mysqld = testing.mysqld.Mysqld(auto_start=0)
        self.assertEqual({'db': 'test', 'unix_socket': mysqld.my_cnf['socket'], 'user': 'root'},
                         mysqld.dsn())
        self.assertEqual("mysql+pymysql://root@localhost/test?unix_socket=%s" % mysqld.my_cnf['socket'],
                         mysqld.url())
        self.assertEqual("mysql+pymysql://root@localhost/test?unix_socket=%s&charset=utf8" % mysqld.my_cnf['socket'],
                         mysqld.url(charset='utf8'))
        self.assertEqual("mysql+mysqldb://root@localhost/test?unix_socket=%s" % mysqld.my_cnf['socket'],
                         mysqld.url(driver='mysqldb'))

        mysqld = testing.mysqld.Mysqld(my_cnf={'port': 12345}, auto_start=0)
        self.assertEqual({'db': 'test', 'host': '127.0.0.1', 'port': 12345, 'user': 'root'},
                         mysqld.dsn())
        self.assertEqual("mysql+pymysql://root@127.0.0.1:12345/test", mysqld.url())
        self.assertEqual("mysql+pymysql://root@127.0.0.1:12345/test?charset=utf8", mysqld.url(charset='utf8'))
        self.assertEqual("mysql+mysqldb://root@127.0.0.1:12345/test", mysqld.url(driver='mysqldb'))

    def test_with_mysql(self):
        with testing.mysqld.Mysqld(my_cnf={'skip-networking': None}) as mysqld:
            self.assertIsNotNone(mysqld)

            # connect to mysql
            conn = pymysql.connect(**mysqld.dsn())
            self.assertIsNotNone(conn)
            self.assertTrue(mysqld.is_alive())

        self.assertFalse(mysqld.is_alive())

    def test_multiple_mysql(self):
        mysqld1 = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        mysqld2 = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        self.assertNotEqual(mysqld1.server_pid, mysqld2.server_pid)

        self.assertTrue(mysqld1.is_alive())
        self.assertTrue(mysqld2.is_alive())

    @patch("testing.mysqld.find_program")
    def test_mysqld_is_not_found(self, find_program):
        find_program.side_effect = RuntimeError

        with self.assertRaises(RuntimeError):
            testing.mysqld.Mysqld(my_cnf={'skip-networking': None})

    def test_fork(self):
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        if os.fork() == 0:
            del mysqld
            mysqld = None
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(mysqld.is_alive())  # process is alive (delete mysqld obj in child does not effect)

    def test_stop_on_child_process(self):
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        if os.fork() == 0:
            mysqld.stop()
            os.kill(mysqld.server_pid, 0)  # process is alive (calling stop() is ignored)
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(mysqld.is_alive())  # process is alive (calling stop() in child is ignored)

    def test_copy_data_from(self):
        try:
            tmpdir = tempfile.mkdtemp()

            # create new database
            with testing.mysqld.Mysqld(my_cnf={'skip-networking': None}, base_dir=tmpdir) as mysqld:
                conn = pymysql.connect(**mysqld.dsn())
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
                cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
                conn.commit()

            # create another database from first one
            data_dir = os.path.join(tmpdir, 'var')
            with testing.mysqld.Mysqld(my_cnf={'skip-networking': None}, copy_data_from=data_dir) as mysqld:
                conn = pymysql.connect(**mysqld.dsn())
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM test.hello ORDER BY id')

                self.assertEqual(cursor.fetchall(), ((1, 'hello'), (2, 'ciao')))
        finally:
            rmtree(tmpdir)

    def test_skipIfNotInstalled_found(self):
        @testing.mysqld.skipIfNotInstalled
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    @patch("testing.mysqld.find_program")
    def test_skipIfNotInstalled_notfound(self, find_program):
        find_program.side_effect = RuntimeError

        @testing.mysqld.skipIfNotInstalled
        def testcase():
            pass

        self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
        self.assertEqual(True, testcase.__unittest_skip__)
        self.assertEqual("mysqld not found", testcase.__unittest_skip_why__)

    def test_skipIfNotInstalled_with_args_found(self):
        path = testing.mysqld.find_program('mysqld', ['sbin'])

        @testing.mysqld.skipIfNotInstalled(path)
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_skipIfNotInstalled_with_args_notfound(self):
        @testing.mysqld.skipIfNotInstalled("/path/to/anywhere")
        def testcase():
            pass

        self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
        self.assertEqual(True, testcase.__unittest_skip__)
        self.assertEqual("mysqld not found", testcase.__unittest_skip_why__)

    def test_skipIfNotFound_found(self):
        @testing.mysqld.skipIfNotFound
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    @patch("testing.mysqld.find_program")
    def test_skipIfNotFound_notfound(self, find_program):
        find_program.side_effect = RuntimeError

        @testing.mysqld.skipIfNotFound
        def testcase():
            pass

        self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
        self.assertEqual(True, testcase.__unittest_skip__)
        self.assertEqual("mysqld not found", testcase.__unittest_skip_why__)

    def test_MysqldFactory(self):
        Mysqld = testing.mysqld.MysqldFactory(cache_initialized_db=True)
        with Mysqld() as mysqld1:
            self.assertTrue(mysqld1.settings['copy_data_from'])
            copy_data_from1 = mysqld1.settings['copy_data_from']
            self.assertTrue(os.path.exists(copy_data_from1))
        with Mysqld() as mysqld2:
            self.assertEqual(copy_data_from1, mysqld2.settings['copy_data_from'])
        Mysqld.clear_cache()
        self.assertFalse(os.path.exists(copy_data_from1))

    def test_MysqldFactory_with_initialized_handler(self):
        def handler(mysqld):
            conn = pymysql.connect(**mysqld.dsn())
            with closing(conn.cursor()) as cursor:
                cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
                cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
            conn.commit()
            conn.close()

        Mysqld = testing.mysqld.MysqldFactory(cache_initialized_db=True,
                                              on_initialized=handler)
        try:
            with Mysqld() as mysqld:
                conn = pymysql.connect(**mysqld.dsn())
                with closing(conn.cursor()) as cursor:
                    cursor.execute('SELECT * FROM hello ORDER BY id')
                    self.assertEqual(cursor.fetchall(), ((1, 'hello'), (2, 'ciao')))
                conn.close()
        finally:
            Mysqld.clear_cache()
