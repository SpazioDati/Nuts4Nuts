#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import wikipedia_template_parser as wtp


# globals
TEMPLATES_TO_ANALYZE_IT = {
    u'edificio_religioso': [u'città'],
    u'rifugio': [u'localita'],
    u'edificio_civile': [u'città', u'cittàlink'],
    u'area_protetta': [u'comuni']
}

# logging
logger = logging.getLogger('nuts4nuts.template')


class TemplateAnalyzer(object):

    def __init__(self, page, lang='it'):
        self.abstract = None
        self.page = page
        self.lang = lang

    def _treat(self, name):
        if isinstance(name, unicode):
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def _normalize(name):
        if 'http:':
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def analyze_templates(self):
        logger.debug(self.page)

        templates = wtp.data_from_templates(self.page, self.lang)

        logger.debug(templates)

        for t in templates:
            name = self._treat(t['name'])
            if name in TEMPLATES_TO_ANALYZE_IT.keys():
                attributes = TEMPLATES_TO_ANALYZE_IT[name]
                tdata = {self._treat(k): v for k, v in t['data'].iteritems()}
                return [tdata[attr] for attr in attributes if tdata[attr] != '']


if __name__ == '__main__':
    LOGFORMAT_STDOUT = {logging.DEBUG: '%(module)s:%(funcName)s:%(lineno)s - %(levelname)-8s: %(message)s',
                        logging.INFO: '%(levelname)-8s: %(message)s',
                        logging.WARNING: '%(levelname)-8s: %(message)s',
                        logging.ERROR: '%(levelname)-8s: %(message)s',
                        logging.CRITICAL: '%(levelname)-8s: %(message)s'
                        }

    # --- logging ---
    logger = logging.getLogger()
    console = logging.StreamHandler()

    lvl_config_logger = logging.DEBUG

    console.setLevel(lvl_config_logger)

    formatter = logging.Formatter(LOGFORMAT_STDOUT[lvl_config_logger])
    console.setFormatter(formatter)

    logger.addHandler(console)

    logger.setLevel(logging.DEBUG)

    ta = TemplateAnalyzer('Duomo_di_Milano', lang='it')
    print
    print ta.analyze_templates()

    ta = TemplateAnalyzer('Grattacielo Pirelli', lang='it')
    print
    print ta.analyze_templates()
