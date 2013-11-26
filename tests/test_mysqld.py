# -*- coding: utf-8 -*-

import os
import signal
import unittest
import testing.mysqld
from time import sleep
import pymysql


class TestMysqld(unittest.TestCase):
    def test_basic(self):
        # start mysql server
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        self.assertIsNotNone(mysqld)
        self.assertEqual(mysqld.dsn(),
                         dict(unix_socket=mysqld.base_dir + '/tmp/mysql.sock',
                              user='root',
                              db='test'))

        # connect to mysql
        conn = pymysql.connect(**mysqld.dsn())
        self.assertIsNotNone(conn)
        self.assertRegexpMatches(mysqld.read_log(), 'ready for connections')

        # shutting down
        pid = mysqld.pid
        self.assertTrue(os.path.exists(mysqld.base_dir + '/tmp/mysql.sock'))
        self.assertTrue(pid)
        os.kill(pid, 0)  # process is alive

        mysqld.stop()
        sleep(1)

        self.assertFalse(os.path.exists(mysqld.base_dir + '/tmp/mysql.sock'))
        self.assertIsNone(mysqld.pid)
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

    def test_dsn_and_url(self):
        mysqld = testing.mysqld.Mysqld(auto_start=0)
        self.assertEqual({'db': 'test', 'unix_socket': mysqld.my_cnf['socket'], 'user': 'root'},
                         mysqld.dsn())
        self.assertEqual("mysql://root@localhost/test?unix_socket=%s" % mysqld.my_cnf['socket'],
                         mysqld.url())
        self.assertEqual("mysql://root@localhost/test?unix_socket=%s&charset=utf8" % mysqld.my_cnf['socket'],
                         mysqld.url(charset='utf8'))

        mysqld = testing.mysqld.Mysqld(my_cnf={'port': 12345}, auto_start=0)
        self.assertEqual({'db': 'test', 'host': '127.0.0.1', 'port': 12345, 'user': 'root'},
                         mysqld.dsn())
        self.assertEqual("mysql://root@127.0.0.1:12345/test", mysqld.url())
        self.assertEqual("mysql://root@127.0.0.1:12345/test?charset=utf8", mysqld.url(charset='utf8'))

    def test_with_mysql(self):
        with testing.mysqld.Mysqld(my_cnf={'skip-networking': None}) as mysqld:
            self.assertIsNotNone(mysqld)

            # connect to mysql
            conn = pymysql.connect(**mysqld.dsn())
            self.assertIsNotNone(conn)

            pid = mysqld.pid
            os.kill(pid, 0)  # process is alive

        self.assertIsNone(mysqld.pid)
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

    def test_multiple_mysql(self):
        mysqld1 = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        mysqld2 = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        self.assertNotEqual(mysqld1.pid, mysqld2.pid)

        os.kill(mysqld1.pid, 0)  # process is alive
        os.kill(mysqld2.pid, 0)  # process is alive

    def test_mysqld_is_not_found(self):
        try:
            path = os.environ['PATH']
            os.environ['PATH'] = '/usr/bin'

            with self.assertRaises(RuntimeError):
                testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        finally:
            os.environ['PATH'] = path

    def test_fork(self):
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        if os.fork() == 0:
            del mysqld
            mysqld = None
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(mysqld.pid)
            os.kill(mysqld.pid, 0)  # process is alive (delete mysqld obj in child does not effect)

    def test_stop_on_child_process(self):
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None})
        if os.fork() == 0:
            mysqld.stop()
            self.assertTrue(mysqld.pid)
            os.kill(mysqld.pid, 0)  # process is alive (calling stop() is ignored)
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(mysqld.pid)
            os.kill(mysqld.pid, 0)  # process is alive (calling stop() in child is ignored)

    def test_copy_data_from(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'copy-data-from')
        mysqld = testing.mysqld.Mysqld(my_cnf={'skip-networking': None},
                                       copy_data_from=data_dir)

        # connect to mysql
        conn = pymysql.connect(**mysqld.dsn())
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test.hello ORDER BY id')

        self.assertEqual(cursor.fetchall(), ((1, 'hello'), (2, 'ciao')))
