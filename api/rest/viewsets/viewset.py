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
To make specifying viewsets less tedious and repetitive an extra property
`model_key` is introduced, which can be defined on a ModelViewSetMixin. A
ViewSet can then inherit from mixins, which can be used to automatically
generate an url pattern. This eliminates the need for writing them manually
and multiple times for viewsets with the same model, but a different scope.
"""

__all__ = ("AmCATViewSetMixin", "get_url_pattern", "AmCATViewSetMixinTest")

from collections import OrderedDict
from amcat.tools import amcattest

class AmCATViewSetMixin(object):
    """
    All ViewSet used in the AmCAT API should inherit from this class, or at least
    define a classmethod get_url_pattern(), which returns the pattern for the
    mixin. A default implementation is given for this superclass.
    """
    model_key = None

def get_url_pattern(viewset):
    """
    Get an url pattern (ready to be inserted in urlpatterns()) for `viewset`.

    @type viewset: must inherit from at least one AmCATViewSetMixin
    @rtype: string
    """
    return "/".join(_get_url_pattern(viewset))

def _get_model_keys(viewset):
    """
    Get an iterator of all model_key properties in superclasses. This function
    yields an ordered list, working up the inheritance tree according to Pythons
    MRO algorithm.
    """
    for base in viewset.__bases__:
        if not issubclass(base, AmCATViewSetMixin) or base.model_key is None:
            continue
        for model_key in _get_model_keys(base):
            yield model_key

    if hasattr(viewset, "model_key"):
        yield viewset.model_key

def _get_url_pattern(viewset):
    # Deduplicate (while keeping ordering) with OrderedDict
    model_keys = tuple(OrderedDict.fromkeys(_get_model_keys(viewset)))

    for model_key in model_keys[:-1]:
        yield r"{model_key}s/(?P<{model_key}>\d+)".format(**locals())
    yield r"{model_key}s".format(model_key=model_keys[-1])


######################
##### UNIT TESTS #####
######################

class AmCATViewSetMixinTest(amcattest.PolicyTestCase):
    def test_get_url_pattern(self):
        class AMixin(AmCATViewSetMixin):
            model_key = "project"

        class BMixin(AmCATViewSetMixin):
            model_key = "codebook"

        class CMixin(BMixin):
            pass

        class AViewSet(AMixin, BMixin): pass
        class BViewSet(AMixin, CMixin): pass
        class CViewSet(BMixin, AMixin): pass
            
        self.assertEquals(r"projects", get_url_pattern(AMixin))
        self.assertEquals(r"codebooks", get_url_pattern(BMixin))
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", get_url_pattern(AViewSet))
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", get_url_pattern(BViewSet))
        self.assertEquals(r"codebooks/(?P<codebook>\d+)/projects", get_url_pattern(CViewSet))

