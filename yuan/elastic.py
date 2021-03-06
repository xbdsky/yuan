#!/usr/bin/env python

import json
import requests
from flask import _app_ctx_stack

__all__ = ['ElasticSearch', 'elastic', 'search_project', 'index_project']


class ElasticSearch(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_HOST', 'http://localhost:9200')
        app.config.setdefault('ELASTICSEARCH_INDEX', app.name)

        self.app = app
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['elasticsearch'] = self

    def get_app(self):
        if self.app is not None:
            return self.app
        ctx = _app_ctx_stack.top
        if ctx is not None:
            return ctx.app
        raise RuntimeError(
            'application not registered on ElasticSearch '
            'instance and no application bound to current context'
        )

    def request_base(self):
        app = self.get_app()
        host = app.config.get('ELASTICSEARCH_HOST')
        index = app.config.get('ELASTICSEARCH_INDEX')
        return '%s/%s' % (host, index)

    def get(self, path):
        url = '%s/%s' % (self.request_base(), path)
        req = requests.get(url)
        if req.status_code == 200 or req.status_code == 201:
            return json.loads(req.text)
        raise ValueError('response error %d:%s' % (req.status_code, req.text))

    def post(self, path, data=None):
        url = '%s/%s' % (self.request_base(), path)
        req = requests.post(url, data=json.dumps(data))
        if req.status_code == 200 or req.status_code == 201:
            return json.loads(req.text)
        raise ValueError('response error %d:%s' % (req.status_code, req.text))

    def put(self, path, data=None):
        url = '%s/%s' % (self.request_base(), path)
        req = requests.put(url, data=json.dumps(data))
        if req.status_code == 200 or req.status_code == 201:
            return json.loads(req.text)
        raise ValueError('response error %d:%s' % (req.status_code, req.text))

    def delete(self, path):
        url = '%s/%s' % (self.request_base(), path)
        req = requests.delete(url)
        if req.status_code == 200:
            return json.loads(req.text)
        raise ValueError('response error %d:%s' % (req.status_code, req.text))


elastic = ElasticSearch()


def index_project(project, operation):
    if operation == 'delete':
        elastic.delete('project/%s.%s' % (project.family, project.name))
        return

    if 'packages' not in project:
        return

    package = project.packages[project.version]
    dct = dict(
        family=project.family,
        name=project.name,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
    if 'keywords' in package and isinstance(package['keywords'], list):
        dct['keywords'] = package['keywords']

    if 'description' in package:
        dct['description'] = package['description']

    elastic.post('project/%s.%s' % (project.family, project.name), dct)


def search_project(query):
    if not query:
        return None
    size = 30
    dct = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "name", "family", "keywords", "description"
                ]
            }
        },
        "fields": [
            "name", "family", "homepage", "description", "keywords",
            "created_at", "updated_at"
        ],
        "size": size
    }
    content = elastic.post('project/_search', dct)
    hits = content['hits']

    def _format(item):
        fields = item['fields']
        fields['id'] = item['_id']
        return fields

    results = map(_format, hits['hits'])
    hits['results'] = results
    del hits['hits']
    return hits
