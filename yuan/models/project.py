# coding: utf-8

import os
import gevent
import shutil
from flask import Flask, json
from flask import current_app
from datetime import datetime
from werkzeug import cached_property
from collections import OrderedDict
from distutils.version import StrictVersion
from ._base import project_signal

__all__ = ['Project', 'Package', 'index_project']


class Model(dict):
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __getattr__(self, key):
        try:
            return to_unicode(self[key])
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = to_unicode(value)

    def __getitem__(self, key):
        return to_unicode(super(Model, self).__getitem__(key))

    def __setitem__(self, key, value):
        return super(Model, self).__setitem__(key, to_unicode(value))

    @cached_property
    def datafile(self):
        raise NotImplementedError

    def read(self):
        fpath = self.datafile
        if not os.path.exists(fpath):
            return None
        data = _read_json(fpath)
        for key in data:
            if not key.startswith('_'):
                self[key] = data[key]
        return self

    def save(self):
        fpath = self.datafile

        directory = os.path.dirname(fpath)
        if not os.path.exists(directory):
            os.makedirs(directory)

        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        if 'created_at' not in self:
            self.created_at = now

        with open(fpath, 'w') as f:
            self.updated_at = now
            f.write(json.dumps(self))
            return self

    def delete(self):
        directory = os.path.dirname(self.datafile)
        if os.path.exists(directory):
            return shutil.rmtree(directory)
        return None


class Project(Model):
    def __init__(self, **kwargs):
        self.family = kwargs.pop('family')
        self.name = kwargs.pop('name')
        if not self.read():
            for key in kwargs:
                setattr(self, key, kwargs[key])

    def __str__(self):
        return '%s/%s' % (self.family, self.name)

    def __repr__(self):
        return '<Project: %s>' % self

    def sort(self, versions=None):
        if not versions:
            return {}
        o = OrderedDict()
        for v in sorted(versions.keys(),
                        key=lambda i: StrictVersion(i), reverse=True):
            o[v] = versions[v]
        return o

    @cached_property
    def datafile(self):
        root = current_app.config['WWW_ROOT']
        return os.path.join(
            root, 'repository',
            self.family, self.name,
            'index.json'
        )

    @staticmethod
    def list(family):
        fpath = os.path.join(
            current_app.config['WWW_ROOT'],
            'repository',
            family,
            'index.json'
        )
        return _read_json(fpath)

    def update(self, dct):
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        if 'version' not in dct:
            return False
        if 'family' in dct and dct['family'] != self.family:
            return False
        if 'name' in dct and dct['name'] != self.name:
            return False

        # save package
        dct['family'] = self.family
        dct['name'] = self.name
        pkg = Package(**dct)
        pkg.save()

        versions = self.versions or {}
        if 'readme' in pkg:
            del pkg['readme']
        versions[pkg.version] = pkg

        if 'created_at' not in self:
            self.created_at = now

        self.versions = self.sort(versions)
        self.updated_at = now
        self.write()
        return self

    def remove(self, version):
        if version in self.versions:
            del self.versions[version]

        self.write()
        return self

    def write(self, data=None):
        if not data:
            data = self
        storage = current_app.config['WWW_ROOT']
        directory = os.path.join(
            storage, 'repository', self.family, self.name
        )
        if not os.path.exists(directory):
            os.makedirs(directory)

        fpath = os.path.join(directory, 'index.json')
        with open(fpath, 'w') as f:
            f.write(json.dumps(data))
            return data


class Package(Model):
    def __init__(self, **kwargs):
        self.family = kwargs.pop('family')
        self.name = kwargs.pop('name')
        self.version = kwargs.pop('version')
        if not self.read():
            for key in kwargs:
                setattr(self, key, kwargs[key])

    def __str__(self):
        return '%s/%s@%s' % (self.family, self.name, self.version)

    def __repr__(self):
        return '<Package: %s>' % self

    @cached_property
    def datafile(self):
        storage = current_app.config['WWW_ROOT']
        return os.path.join(
            storage, 'repository',
            self.family, self.name, self.version,
            'index.json'
        )


def index_project(project, operation):
    directory = os.path.join(
        current_app.config['WWW_ROOT'], 'repository', project['family']
    )
    fpath = os.path.join(directory, 'index.json')
    data = _read_json(fpath)
    data = filter(lambda o: o['name'] != project['name'], data)

    if operation == 'delete':
        directory = os.path.join(directory, project['name'])
        if os.path.exists(directory):
            shutil.rmtree(directory)
        with open(fpath, 'w') as f:
            f.write(json.dumps(data))
        return data

    if not os.path.exists(directory):
        os.makedirs(directory)

    data.append(project)
    data = sorted(
        data,
        key=lambda o: datetime.strptime(o['updated_at'], '%Y-%m-%dT%H:%M:%SZ'),
        reverse=True
    )
    with open(fpath, 'w') as f:
        f.write(json.dumps(data))
        return data


def to_unicode(value):
    if isinstance(value, unicode):
        return value
    if isinstance(value, basestring):
        return value.decode('utf-8')
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value


def _read_json(fpath):
    if not os.path.exists(fpath):
        return {}
    with open(fpath, 'r') as f:
        content = f.read()
        try:
            return json.loads(content)
        except:
            return {}


def _connect_project(sender, changes):
    project, operation = changes

    def _index(config):
        app = Flask('yuan')
        app.config = config
        with app.test_request_context():
            index_project(project, operation)

    gevent.spawn(_index, current_app.config)


project_signal.connect(_connect_project)
