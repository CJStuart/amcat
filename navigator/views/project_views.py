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

from navigator.views.datatableview import DatatableMixin
from django.views.generic.list import ListView
from api.rest.datatable import FavouriteDatatable
from amcat.models import Project
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin

class ProjectListView(BreadCrumbMixin, DatatableMixin, ListView):
    model = Project
    context_category = 'Articles'
    template_name = "project/project_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(ProjectListView, self).get_context_data(**kwargs)

        context["main_active"] = 'Projects'
        return context



    def get_breadcrumbs(self):
        return [("Projects", "#")]
        
    def get_datatable(self):
        """Create the Datatable object"""

        url = reverse('project', args=[123])
        table = FavouriteDatatable(resource=self.get_resource(), label="project",
                                   set_url=url + "?star=1", unset_url=url+"?star=0")
        table = table.rowlink_reverse('project', args=['{id}'])
        #table = table.rowlink_reverse('article set-details', args=[self.project.id, '{id}'])
        #table = table.hide("project")
        table = self.filter_table(table)
        return table
