from django import forms
from webscript import WebScript
from django.template.loader import render_to_string

import amcat.scripts.forms
import amcat.forms
from amcat.tools import keywordsearch

from amcat.scripts import script

#from amcat.scripts.searchscripts.articlelist import ArticleListScript, ArticleListSpecificForm

from amcat.scripts.searchscripts.articlelist import ArticleListScript

    
class ShowSummary(WebScript):
    name = "Summary"
    form_template = None
    form = None
    
    def run(self):

        if isinstance(self.data['projects'], (basestring, int)):
            project_id = int(self.data['projects'])
        else:
            project_id = int(self.data['projects'][0])
        
        n = keywordsearch.get_total_n(self.data)
        articles = list(ArticleListScript(self.data).run())
        for a in articles:
            a.hack_project_id = project_id
        self.output_template = 'api/webscripts/articlelist.html'
            
        return self.outputResponse(dict(articlelist=articles, n=n, page=self.data.get('start')), ArticleListScript.output_type)
        
