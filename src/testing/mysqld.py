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
import sys
import signal
import pymysql
import tempfile
import subprocess
from time import sleep
from shutil import copytree

__all__ = ['Mysqld']

SEARCH_PATHS = ['/usr/local/mysql']
DEFAULT_SETTINGS = dict(auto_start=2,
                        base_dir=None,
                        mysql_install_db=None,
                        mysqld=None,
                        pid=None,
                        copy_data_from=None)


class Mysqld(object):
    def __init__(self, **kwargs):
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings.update(kwargs)
        self.pid = None
        self._owner_pid = os.getpid()

        if self.base_dir:
            if self.base_dir[0] != '/':
                self.settings['base_dir'] = os.path.join(os.getcwd(), self.base_dir)
        else:
            self.settings['base_dir'] = tempfile.mkdtemp()
            self._use_tmpdir = True

        my_cnf = self.settings.setdefault('my_cnf', {})
        my_cnf.setdefault('socket', os.path.join(self.base_dir, 'tmp', 'mysql.sock'))
        my_cnf.setdefault('datadir', os.path.join(self.base_dir, 'var'))
        my_cnf.setdefault('pid-file', os.path.join(self.base_dir, 'tmp', 'mysqld.pid'))
        my_cnf.setdefault('tmpdir', os.path.join(self.base_dir, 'tmp'))

        if self.mysql_install_db is None:
            self.settings['mysql_install_db'] = find_program('mysql_install_db', ['bin', 'scripts'])

        if self.mysqld is None:
            self.settings['mysqld'] = find_program('mysqld', ['bin', 'libexec', 'sbin'])

        if self.auto_start:
            if os.path.exists(self.my_cnf['pid-file']):
                raise RuntimeError('mysqld is already running (%s)' % self.my_cnf['pid-file'])

            if self.auto_start >= 2:
                self.setup()

            self.start()

    def __del__(self):
        import os
        if self.pid and self._owner_pid == os.getpid():
            self.stop()
            self.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        import os
        if self.pid and self._owner_pid == os.getpid():
            self.stop()
            self.cleanup()

    def cleanup(self):
        from shutil import rmtree
        if self._use_tmpdir:
            rmtree(self.base_dir)

    def __getattr__(self, name):
        if name in self.settings:
            return self.settings[name]
        else:
            raise AttributeError("'Mysqld' object has no attribute '%s'" % name)

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

        params.setdefault('user', 'root')
        params.setdefault('db', 'test')

        return params

    def start(self):
        if self.pid:
            return  # already started

        logger = open(os.path.join(self.base_dir, 'tmp', 'mysqld.log'), 'wt')
        pid = os.fork()
        if pid == 0:
            os.dup2(logger.fileno(), sys.__stdout__.fileno())
            os.dup2(logger.fileno(), sys.__stderr__.fileno())

            try:
                os.execl(self.mysqld, self.mysqld,
                         '--defaults-file=%s/etc/my.cnf' % self.base_dir,
                         '--user=root')
            except Exception as exc:
                raise RuntimeError('failed to launch mysqld: %r' % exc)
        else:
            logger.close()

            while not os.path.exists(self.my_cnf['pid-file']):
                if os.waitpid(pid, os.WNOHANG) != (0, 0):
                    raise RuntimeError("*** failed to launch mysqld ***\n" + self.read_log())

                sleep(0.1)

            self.pid = pid

            # create test database
            conn = pymysql.connect(**self.dsn())
            conn.query('CREATE DATABASE IF NOT EXISTS test')
            conn.close()

    def stop(self, _signal=signal.SIGTERM):
        import os
        if self.pid is None:
            return  # not started

        if self._owner_pid != os.getpid():
            return  # could not stop in child process

        try:
            os.kill(self.pid, _signal)
            while (os.waitpid(self.pid, 0)):
                pass
        except:
            pass

        self.pid = None

        try:
            # might remain for example when sending SIGKILL
            os.unlink(self.my_cnf['pid-file'])
        except:
            pass

    def setup(self):
        # copy data files
        if self.copy_data_from:
            try:
                copytree(self.copy_data_from, self.my_cnf['datadir'])
            except Exception as exc:
                raise RuntimeError("could not copytree %s to %s: %r" %
                                   (self.copy_data_from, self.my_cnf['datadir'], exc))

        # (re)create directory structure
        for subdir in ['etc', 'var', 'tmp']:
            try:
                path = os.path.join(self.base_dir, subdir)
                os.makedirs(path)
            except:
                pass

        # my.cnf
        with open(os.path.join(self.base_dir, 'etc', 'my.cnf'), 'wt') as my_cnf:
            my_cnf.write("[mysqld]\n")
            for key, value in self.my_cnf.items():
                if value:
                    my_cnf.write("%s=%s\n" % (key, value))
                else:
                    my_cnf.write("%s\n" % key)

        # mysql_install_db
        if not os.path.exists(os.path.join(self.base_dir, 'var', 'mysql')):
            args = []
            args.append(self.mysql_install_db)

            # We should specify --defaults-file option first.
            args.append("--defaults-file=%s/etc/my.cnf" % self.base_dir)

            mysql_base_dir = self.mysql_install_db
            if os.path.islink(mysql_base_dir):
                mysql_base_dir = os.path.abspath(os.readlink(mysql_base_dir))

            if re.search('[^/]+/mysql_install_db$', mysql_base_dir):
                args.append("--basedir=%s" % re.sub('[^/]+/mysql_install_db$', '', mysql_base_dir))

            try:
                subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
            except Exception as exc:
                raise RuntimeError("failed to spawn mysql_install_db: %r" % exc)

    def read_log(self):
        try:
            with open(os.path.join(self.base_dir, 'tmp', 'mysqld.log')) as log:
                return log.read()
        except Exception as exc:
            raise RuntimeError("failed to open file:tmp/mysqld.log: %r" % exc)


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


def get_path_of(name):
    path = subprocess.Popen(['which', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
    if path:
        return path.rstrip().decode('utf-8')
    else:
        return None
