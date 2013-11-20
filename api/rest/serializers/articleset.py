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
from django.db.models import Q
from rest_framework import serializers
from amcat.models import ArticleSet
from amcat.tools import amcates
from api.rest.serializer import AmCATModelSerializer


class ArticleSetSerializer(AmCATModelSerializer):
    favourite = serializers.SerializerMethodField("is_favourite")
    articles = serializers.SerializerMethodField("n_articles")

    def cache_results(self):
        """
        Cache results for favourite projects and articles per set
        """
        # Only cache once! (is this a hack?)
        self.cache_results = lambda : None

        try:
            # HACK!
            project = self.context['request'].GET['project_for_favourites']
        except KeyError:
            # no project given, so nothing to do :-(
            self.fav_articlesets = None
            self.nn = None
            return

        self.fav_articlesets = set(ArticleSet.objects.filter(favourite_of_projects=project)
                                   .values_list("id", flat=True))
        sets = list(ArticleSet.objects.filter(Q(project=project)|Q(projects_set=project)).values_list("id", flat=True))
        self.nn = dict(amcates.ES().aggregate_query(filters={'sets' : sets}, group_by='sets'))

        self._cached = True

    def n_articles(self, articleset):
        self.cache_results()
        if self.nn is not None:
            return self.nn.get(articleset.id)

    def is_favourite(self, articleset):
        self.cache_results()
        if self.fav_articlesets is None:
            return None
        else:
            return articleset.id in self.fav_articlesets

    class Meta:
        model = ArticleSet


class _NoProjectRequestedError(ValueError): pass