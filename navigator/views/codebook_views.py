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

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView

from django import forms

from api.rest.datatable import Datatable
from amcat.models import Language
from amcat.scripts.actions.import_codebook import ImportCodebook
from amcat.scripts.actions.export_codebook import ExportCodebook
from amcat.scripts.actions.export_codebook_as_xml import ExportCodebookAsXML
from api.rest.viewsets import CodebookViewSet
from navigator.views.project_views import ProjectDetailsView
from navigator.views.scriptview import TableExportMixin
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectFormView
from amcat.models import Codebook
from amcat.forms import widgets

    
class ExportCodebook(TableExportMixin, ProjectScriptView):
    script = ExportCodebook

    def export_filename(self, form):
        c = form.cleaned_data["codebook"]
        return "Codebook {c.id} {c}".format(**locals())
    
    def get_initial(self):
        initial = super(ExportCodebook, self).get_initial()
        initial["codebook"]=self.url_data["codebookid"]
        return initial

    def get_form_class(self):
        # Modify form class to also contain XML output
        form_class = super(ExportCodebook, self).get_form_class()
        form_class.base_fields['format'].choices.append(("xml", "XML"))
        return form_class

    def get_form(self, *args, **kargs): 
        form = super(ExportCodebook, self).get_form(*args, **kargs)
        cid=self.url_data["codebookid"]
        langs = Language.objects.filter(labels__code__codebook_codes__codebook_id=cid).distinct()
        form.fields['language'].queryset = langs
        form.fields['language'].initial = min(l.id for l in langs)
        return form

    def form_valid(self, form):
        if form.cleaned_data['format'] == 'xml':
            return ExportCodebookXML.as_view()(self.request, **self.kwargs)

        return super(ExportCodebook, self).form_valid(form)

class ExportCodebookXML(ProjectScriptView):
    script = ExportCodebookAsXML

    def export_filename(self, form):
        c = form.cleaned_data["codebook"]
        return "Codebook {c.id} {c}.xml".format(**locals())

    def get_initial(self):
        return dict(codebook=self.url_data["codebookid"])

    def form_valid(self, form):
        super(ExportCodebookXML, self).form_valid(form)

        filename = self.export_filename(form)
        response = HttpResponse(self.result, content_type='text/xml', status=200)
        response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
        return response

class AddCodebookView(RedirectView):
    """
    Add codebook automatically creates an empty codebook and opens the edit codebook page
    """
    def get_redirect_url(self, project_id, **kwargs):
        c = Codebook.objects.create(project_id=project_id, name='New codebook')
        return reverse('codebook-details', args=[project_id, c.id])



class CodebookListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, ListView):
    model = Codebook
    parent = ProjectDetailsView
    context_category = 'Coding'
    view_name = "coding codebook-list"


    def get_context_data(self, **kwargs):
        ctx = super(CodebookListView, self).get_context_data(**kwargs)
        all_codebooks = Datatable(CodebookViewSet, rowlink='./{id}', url_kwargs={"project" : self.project.id})
        owned_codebooks = all_codebooks.filter(project=self.project)
        linked_codebooks = all_codebooks.filter(projects_set=self.project)

        ctx.update(locals())
        return ctx

class CodebookDetailsView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DetailView):
    parent = CodebookListView
    view_name = "coding codebook-details"

class CodebookImportView(ProjectScriptView):
    script = ImportCodebook
    parent = CodebookListView
    url_fragment = 'import'

    def get_initial(self):
        initial = super(CodebookImportView, self).get_initial()
        initial["codebook"]=self.kwargs.get("codebookid")
        return initial
    
class CodebookLinkView(ProjectFormView):
    parent = CodebookListView
    url_fragment = 'link'

    class form_class(forms.Form):
        codebooks = forms.MultipleChoiceField(widget=widgets.JQueryMultipleSelect)

    def get_form(self, form_class):
        form = super(CodebookLinkView, self).get_form(form_class)
        from navigator.forms import gen_coding_choices
        form.fields['codebooks'].choices = gen_coding_choices(self.request.user, Codebook)
        return form
