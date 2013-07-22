#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import requests
import json

# logging
logger = logging.getLogger('nuts4nuts.nuts')


class NutsRecon():
    '''
    Query the NUTS reconciliation service:
        http://nuts.spaziodati.eu/
    '''

    def __init__(self):
        self.RECONCILE_URL = 'http://nuts.spaziodati.eu/reconcile'
        self.SUGGEST_URL = 'http://nuts.spaziodati.eu/suggest'

    def query(self, query):
        request = json.dumps({
            'q0': {'query': query}})
        return requests.get(self.RECONCILE_URL, params={'queries': request}).json()['q0']['result']
