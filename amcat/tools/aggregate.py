###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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
Contains all logic for
"""

# We might want to be a bit more clever here: we assume querying per medium / term is always
# more efficient than querying per interval. This is not true for a large amount of mediums and
# a small amount of dates (status reports for scrapers tend to have this).
from operator import itemgetter
from amcat.models import Medium
from amcat.tools.amcates import ES
from amcat.tools.toolkit import DefaultOrderedDict

import logging
log = logging.getLogger(__name__)


VALID_X_AXES = {"medium", "term"}
VALID_Y_AXES = {"date", "total"}

# We can call transpose() on 'invalid' x / y axes.
VALID_AXES = VALID_X_AXES | VALID_Y_AXES

# Natively supported by elasticsearch.
VALID_INTERVALS = {'year', 'quarter', 'month', 'week', 'day'}


class _HashDict(dict):
    def __hash__(self):
        return hash(frozenset(self.iteritems()))


def _get_pivot(row, column):
    for c, value in row:
        if c == column:
            return float(value)
    return 0.0


def make_relative(aggregation, column):
    # TODO: We should probably make aggregation an ordered dict of ordered
    # TODO: dicts, thus making this algorithm run more cheaply.
    pivots = (_get_pivot(row[1], column) for row in aggregation)
    for pivot, (row, row_values) in zip(pivots, aggregation):
        if not pivot:
            continue

        yield row, tuple((col, value / pivot) for col, value in row_values)


def sort(aggregate, func=itemgetter(0), reverse=False):
    for x, y_values in sorted(aggregate, key=func, reverse=reverse):
        yield x, sorted(y_values, key=func, reverse=reverse)


def transpose(aggregate):
    """
    Transposes an aggregation generated by one of the aggregation functions. For example:

    transpose((
        (1000000003, ((2014, 1), (2015, 1))),
        (1000000008, ((2000, 1),          ))
    ))

    would result in:

    (
        (2014, ((1000000003, 1),)),
        (2015, ((1000000003, 1),)),
        (2000, ((1000000008, 1),))
    )
    """
    transposed = DefaultOrderedDict(list)

    for x_value, y_values in aggregate:
        for y_value, aggregate_value in y_values:
            transposed[y_value].append((x_value, aggregate_value))

    return tuple((k, tuple(v)) for k, v in transposed.items())


def _get_columns(aggregate):
    for _, row_values in aggregate:
        for column, _ in row_values:
            yield column


def _get_row(columns, row, default):
    return tuple(row.get(c, default) for c in columns)


def _to_table(aggregate, default):
    columns = tuple(set(_get_columns(aggregate)))

    yield ("",) + columns
    for row_name, row_values in aggregate:
        yield (row_name,) + _get_row(columns, dict(row_values), default)


def to_table(aggregate, default=0):
    """
    Returns sorted, 2D table for given aggregate. If a value is not found for a
    particular cell, use `default` to fill it. This function does not make any
    promises about column / row order.

    :param aggregate: aggregate
    :return: list of lists, representing a table
    """
    return _to_table(transpose(aggregate), default)


def _aggregate_query(es, query, filters, group_by=None, interval="month"):
    if group_by is None:
        return (("#", es.count(query, filters)),)
    return tuple(es.aggregate_query(query, filters, group_by, date_interval=interval))


def aggregate_by_medium(query, filters, group_by=None, interval="month"):
    """

    :param query:
    :param filters:
    :param group_by:
    :param interval:
    :return:
    """
    es = ES()
    for medium_id in es.list_media(query, filters):
        filters["mediumid"] = [medium_id]
        yield medium_id, _aggregate_query(es, query, filters, group_by, interval)


def aggregate_by_term(queries, filters, group_by=None, interval="month"):
    """

    :param queries:
    :param filters:
    :param group_by:
    :param interval:
    :return:
    """
    es = ES()

    queries = (q for q in queries if q.declared_label is not None)
    queries = ((q.label, q.query) for q in queries)

    for term, query in queries:
        yield term, _aggregate_query(es, query, filters, group_by, interval)


def _aggregate(query, queries, filters, x_axis, y_axis, interval="month"):
    # 'Total' means a 1D aggregation
    y_axis = None if y_axis == "total" else y_axis

    if x_axis == "medium":
        return aggregate_by_medium(query, filters, y_axis, interval)

    if x_axis == "term":
        return aggregate_by_term(queries, filters, y_axis, interval)

    if x_axis == "articleset":
        raise NotImplemented("Aggregating by articleset not yet implemented.")

    if y_axis is None:
        # We can always aggregate if we just aggregate on total count
        return (("#", _aggregate_query(ES(), query, filters, x_axis, interval)),)

    raise ValueError("Invalid x_axis '{x_axis}'".format(**locals()))


def _set_medium_labels(aggregate):
    mediums = Medium.objects.filter(id__in=[a[0] for a in aggregate])
    mediums = dict(mediums.values_list("id", "name"))
    return [(_HashDict({'id': mid, 'label': mediums[mid]}), rest)
            for mid, rest in aggregate]


def _set_term_labels(aggregate, queries):
    queries = {q.label: q.query for q in queries}
    return [(_HashDict({'id': label, 'label': queries[label]}), rest)
            for label, rest in aggregate]


def _set_labels(aggregate, queries, axis):
    if axis == "medium":
        return _set_medium_labels(aggregate)

    if axis == "term":
        return _set_term_labels(aggregate, queries)

    return aggregate


def set_labels(aggregate, queries, x_axis, y_axis):
    """
    Replace id's in aggregation with labels.

    :param aggregate:
    :param x_axis:
    :param y_axis:
    """
    x_axis = _set_labels(aggregate, queries, x_axis)
    y_axis = transpose(_set_labels(transpose(aggregate), queries, y_axis))
    return [(x[0], y[1]) for x, y in zip(x_axis, y_axis)]


def aggregate(query, queries, filters, x_axis, y_axis, interval="month"):
    """
    Elasticsearch doesn't support aggregating on two variables by default, so we need to
    work around it by querying multiple times for each point on `x_axis`.

    :param query: full query
    :type query: unicode, str

    :param queries: splitted query
    :type queries: list of SearchQuery

    :param filters: filters for elasticsearch (see: ES.query)
    :type filters: dict

    :param x_axis:
    :param y_axis:

    :return:
    """
    if x_axis not in VALID_AXES:
        raise ValueError("{x_axis} is not a valid axis. Choose one of: {VALID_AXES}".format(**dict(globals(), **locals())))

    if y_axis not in VALID_AXES:
        raise ValueError("{y_axis} is not a valid axis. Choose one of: {VALID_AXES}".format(**dict(globals(), **locals())))

    if x_axis == y_axis:
        raise ValueError("y_axis and x_axis cannot be the same")

    # We need to transpose the result matrix if given x_axis is a valid
    needs_transposing = False
    if x_axis == "total":
        # Total can only be aggregated on y_axis. Transpose!
        needs_transposing = True
    elif y_axis != "total":
        # If we do not aggregate on total, we have to check x/y for validity
        needs_transposing = x_axis not in VALID_X_AXES and y_axis in VALID_X_AXES

    if needs_transposing:
        aggr = transpose(_aggregate(query, queries, filters, y_axis, x_axis, interval))
    else:
        aggr = _aggregate(query, queries, filters, x_axis, y_axis, interval)

    return list(aggr)

# Unittests: amcat.tools.tests.aggregate
