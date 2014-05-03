###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Script to be run daily after daily.py, checking it's success and reporting to admins in case of failure (via mail)
"""

from amcat.models.scraper import Scraper
from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.scripts.script import Script
from amcat.tools import toolkit, sendmail

import logging;log = logging.getLogger(__name__)
import os
from django import forms
from datetime import date, timedelta


MAIL_HTML = """<h3>Report for daily scraping on {datestr}</h3>

<p>The following scrapers were run:</p>
{table}

<p>For log details, ssh to amcat-dev.labs.vu.nl, then open /home/amcat/log/daily_{_date.year:04d}-{_date.month:02d}-{_date.day:02d}.txt</p>

<p>For a complete overview of last week's results, navigate <a href="http://amcat.vu.nl/navigator/scrapers">here</a>.</p>
"""

    
class ScrapingCheckForm(forms.Form):
    date = forms.DateField()
    mail_to = forms.CharField()

class ScrapingCheck(Script):
    options_form = ScrapingCheckForm

    def run(self, _input):
        log.info("starting.. getting data")
        result = self.get_result()
        self.send_mail(result)

    def make_table(self, result):
        from amcat.tools.table.table3 import DictTable, SortedTable
        from amcat.tools.table.tableoutput import table2html
        table = DictTable()
        for scraper, res in result.items():
            succ, data = res
            table.addValue(
                row = scraper,
                col = "success days",
                value = succ
                )
            table.addValue(
                row = scraper,
                col = "id",
                value = scraper.id
                )
            table.addValue(
                row = scraper,
                col = "set",
                value = scraper.articleset.id
                )
            table.addValue(
                row = scraper,
                col = "project",
                value = scraper.articleset.project.id
                )
            for day, n in data.items():
                table.addValue(
                    row = scraper,
                    col = day,
                    value = n
                    )        
        return table2html(table, sortcolumns = True,reversesort = True)

    def send_mail(self, result):        
        table = self.make_table(result)
        datestr = toolkit.writeDate(self.options['date'])
        subject = "Daily scraping for {datestr}".format(**locals())
        _date = self.options['date']
        content = MAIL_HTML.format(**locals())
        for addr in self.options['mail_to'].split(","):
            sendmail.sendmail("toon.alfrink@gmail.com",
                     addr, subject, content, None)

    def get_result(self):
        out = {}
        dates = toolkit.daterange(self.options['date'] - timedelta(days = 6),self.options['date'])
        for scraper in Scraper.objects.filter(active=True,run_daily=True):
            succ = 0
            n_scraped = scraper.n_scraped_articles(
                from_date = dates[0],
                to_date = dates[-1],
                medium = Medium.get_or_create(scraper.get_scraper_class().medium_name)
                )

            for day in dates:
                if scraper.statistics:
                    n_expected = scraper.statistics[day.weekday()]
                    if n_scraped[day] >= n_expected[0]:
                        succ += 1
                else:
                    if n_scraped[day] > 0:
                        succ += 1
            out[scraper] = (succ,n_scraped)
        from pprint import pprint
        pprint(out)
        return out

if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(ScrapingCheck)
