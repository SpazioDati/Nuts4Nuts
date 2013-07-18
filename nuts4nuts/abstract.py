#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import wikipedia_template_parser as wtp
import dewiki
import logging
from dbpedia_querist import DBpediaQuerist, SPARQLQueryBuilder

# globals
DBPEDIARESURL = {'it': u'http://it.dbpedia.org/resource/',
                 'en': u'http://dbpedia.org/resource'
                 }

QUERYBASE = u'<{page}> <http://dbpedia.org/ontology/abstract> ?o'

SECTIONREGEX = re.compile('==[^=]*==', re.IGNORECASE)


# --- logging
logger = logging.getLogger('nuts4nuts.abstract')


class AbstractGetter(object):

    def __init__(self, page, lang='it'):
        self.abstract = None
        self.lang = lang
        self.page = page
        self.dbq = DBpediaQuerist(self.lang)
        self.qb = SPARQLQueryBuilder().select('*')

        self.pageurl = DBPEDIARESURL[lang]+page.decode('latin1').replace(' ', '_')
        self.qb.where(QUERYBASE.format(page=self.pageurl))

    def get_abstract(self):
        logger.debug(self.page)

        if self.abstract:
            return self.abstract
        else:
            resdb = self.dbq.query(self.qb)

            if resdb:
                try:
                    self.abstract = resdb[0][0].value
                except:
                    logger.error('Error getting abstract from DBpedia: page'.format(
                                 page=self.page))

            if self.abstract is None:
                try:
                    wikitext = wtp.get_wikitext_from_api(self.page,
                                                         lang=self.lang)
                except ValueError:
                    wikitext = ''

                match = SECTIONREGEX.search(wikitext)

                if match:
                    start = match.start()
                    wikitext = wikitext[:start]
                self.abstract = dewiki.from_string(wikitext).strip()

            return self.abstract

if __name__ == '__main__':

    ag = AbstractGetter('Duomo_di_Milano')
    print ag.get_abstract()
