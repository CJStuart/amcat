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

import json
import logging

from amcat.models import Plugin
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

log = logging.getLogger(__name__)


class PluginResource(AmCATResource):
    model = Plugin
    extra_filters = ["plugin_type"]
    queryset = Plugin.objects.all()

    class serializer_class(AmCATModelSerializer):
        class Meta:
            model = Plugin


