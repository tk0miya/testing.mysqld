# -*- coding: utf-8 -*-
#  Copyright 2013 Takeshi KOMIYA
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import re
import pymysql
import subprocess
from contextlib import closing

from testing.common.database import (
    Database, DatabaseFactory, SkipIfNotInstalledDecorator, get_path_of, get_unused_port
)

__all__ = ['Mysqld', 'skipIfNotFound']

SEARCH_PATHS = ['/usr/local/mysql']


class Mysqld(Database):
    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            mysql_install_db=None,
                            mysqld=None,
                            pid=None,
                            port=None,
                            copy_data_from=None,
                            user="root",
                            passwd=None)
    subdirectories = ['etc', 'var', 'tmp']

    def initialize(self):
        self.my_cnf = self.settings.get('my_cnf', {})
        self.my_cnf.setdefault('socket', os.path.join(self.base_dir, 'tmp', 'mysql.sock'))
        self.my_cnf.setdefault('datadir', os.path.join(self.base_dir, 'var'))
        self.my_cnf.setdefault('pid-file', os.path.join(self.base_dir, 'tmp', 'mysqld.pid'))
        self.my_cnf.setdefault('tmpdir', os.path.join(self.base_dir, 'tmp'))

        self.mysql_install_db = self.settings.get('mysql_install_db')
        if self.mysql_install_db is None:
            self.mysql_install_db = find_program('mysql_install_db', ['bin', 'scripts'])

        self.mysqld = self.settings.get('mysqld')
        if self.mysqld is None:
            self.mysqld = find_program('mysqld', ['bin', 'libexec', 'sbin'])

    def dsn(self, **kwargs):
        params = dict(kwargs)

        if 'port' in self.my_cnf:
            params.setdefault('port', self.my_cnf['port'])

        if 'port' in params:
            if 'bind-address' in self.my_cnf:
                params.setdefault('host', self.my_cnf['bind-address'])
            else:
                params.setdefault('host', '127.0.0.1')
        else:
            params.setdefault('unix_socket', self.my_cnf['socket'])

        params.setdefault('user', self.settings.get('user'))
        passwd = self.settings.get('passwd')
        if passwd:
            params.setdefault('passwd', passwd)
        params.setdefault('db', 'test')

        return params

    def url(self, **kwargs):
        params = self.dsn(**kwargs)

        driver = params.get('driver', 'pymysql')

        if 'port' in params:
            url = ('mysql+%s://%s@%s:%d/%s' %
                   (driver, params['user'], params['host'], params['port'], params['db']))

            if 'charset' in params:
                url += "?charset=%s" % params['charset']
        else:
            url = ('mysql+%s://%s@localhost/%s?unix_socket=%s' %
                   (driver, params['user'], params['db'], params['unix_socket']))

            if 'charset' in params:
                url += "&charset=%s" % params['charset']

        return url

    def get_data_directory(self):
        return self.my_cnf['datadir']

    def initialize_database(self):
        # assign port if networking not disabled
        if 'port' not in self.my_cnf and 'skip-networking' not in self.my_cnf:
            self.my_cnf['port'] = get_unused_port()

        # my.cnf
        with open(os.path.join(self.base_dir, 'etc', 'my.cnf'), 'wt') as my_cnf:
            my_cnf.write("[mysqld]\n")
            for key, value in self.my_cnf.items():
                if value:
                    my_cnf.write("%s=%s\n" % (key, value))
                else:
                    my_cnf.write("%s\n" % key)

        # initialize databse
        if not os.path.exists(os.path.join(self.base_dir, 'var', 'mysql')):
            args = ["--defaults-file=%s/etc/my.cnf" % self.base_dir,
                    "--datadir=%s" % self.my_cnf['datadir']]

            mysql_base_dir = self.mysql_install_db
            if os.path.islink(mysql_base_dir):
                link = os.readlink(mysql_base_dir)
                mysql_base_dir = os.path.join(os.path.dirname(mysql_base_dir),
                                              link)
                mysql_base_dir = os.path.normpath(mysql_base_dir)

            if re.search('[^/]+/mysql_install_db$', mysql_base_dir):
                args.append("--basedir=%s" % re.sub('[^/]+/mysql_install_db$', '', mysql_base_dir))

            try:
                mysqld_args = [self.mysqld] + args + ["--initialize-insecure"]
                mysqld = subprocess.Popen(mysqld_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                mysqld.communicate()

                if mysqld.returncode:  # MySQL < 5.7
                    install_db_args = [self.mysql_install_db] + args
                    subprocess.Popen(install_db_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
            except Exception as exc:
                raise RuntimeError("failed to spawn mysql_install_db: %r" % exc)

    def get_server_commandline(self):
        return [self.mysqld,
                '--defaults-file=%s/etc/my.cnf' % self.base_dir,
                '--user=root']

    def is_server_available(self):
        return os.path.exists(self.my_cnf['pid-file'])

    def poststart(self):
        # create test database
        params = self.dsn()
        del params['db']
        with closing(pymysql.connect(**params)) as conn:
            conn.query('CREATE DATABASE IF NOT EXISTS test')


class MysqldFactory(DatabaseFactory):
    target_class = Mysqld


class MysqldSkipIfNotInstalledDecorator(SkipIfNotInstalledDecorator):
    name = 'mysqld'

    def search_server(self):
        find_program('mysqld', ['bin', 'libexec', 'sbin'])


skipIfNotFound = skipIfNotInstalled = MysqldSkipIfNotInstalledDecorator()


def find_program(name, subdirs):
    path = get_path_of(name)
    if path:
        return path

    mysql_paths = [os.path.join(dir, 'bin', 'mysql') for dir in SEARCH_PATHS] + \
                  [get_path_of('mysql')]
    for mysql_path in mysql_paths:
        if mysql_path and os.path.exists(mysql_path):
            for subdir in subdirs:
                replace = '/%s/%s' % (subdir, name)
                path = re.sub('/bin/mysql$', replace, mysql_path)
                if os.path.exists(path):
                    return path

    raise RuntimeError("command not found: %s" % name)
