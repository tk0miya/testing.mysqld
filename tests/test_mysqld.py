# -*- coding: utf-8 -*-

import os
import unittest
import test.mysqld
from time import sleep
import pymysql


class TestMysqld(unittest.TestCase):
    def test_basic(self):
        # start mysql server
        mysqld = test.mysqld.Mysqld(my_cnf={'skip-networking': None})
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
