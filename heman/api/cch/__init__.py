from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import time

from flask import current_app, jsonify, request, Response
from pymongo import ASCENDING

from heman.api import AuthorizedResource
from heman.auth import check_cups_allowed
from heman.config import mongo


class CCHResource(AuthorizedResource):
    method_decorators = (
            AuthorizedResource.method_decorators + [check_cups_allowed]
    )

    def options(self, *args, **kwargs):
        return jsonify({})


WATT = 'W'
KILOWATT = 'kW'
P1_CURVE_TYPE = 'p'


class CCHFact(CCHResource):

    def get_cursor_db(self, collection, query):
        return mongo.db[collection].find(
            query,
            fields={'_id': False, 'datetime': True, 'ai': True}).sort(
            'datetime', ASCENDING
        )

    def _curve_value(self, curve, unit):
        return {
            'date': time.mktime((curve['datetime']).timetuple()) * 1000,
            'value': curve['ai'] * 1000 if unit == KILOWATT else curve['ai']
        }

    def ordered_merge(self, cursor_f1, cursor_p1):
        curves = []
        f1_curve = next(cursor_f1, False)
        p1_curve = next(cursor_p1, False)
        while f1_curve and p1_curve:
            if f1_curve['datetime'] == p1_curve['datetime']:
                curves.append(self._curve_value(f1_curve, KILOWATT))
                f1_curve = next(cursor_f1, False)
                p1_curve = next(cursor_p1, False)
            elif f1_curve['datetime'] < p1_curve['datetime']:
                curves.append(self._curve_value(f1_curve, KILOWATT))
                f1_curve = next(cursor_f1, False)
            else:
                curves.append(self._curve_value(p1_curve, KILOWATT))
                p1_curve = next(cursor_p1, False)

        while f1_curve:
            curves.append(self._curve_value(f1_curve, KILOWATT))
            f1_curve = next(cursor_f1, False)
        while p1_curve:
            curves.append(self._curve_value(p1_curve, KILOWATT))
            p1_curve = next(cursor_p1, False)

        return curves

    def _query_result_length(self, result):
        return result.count()

    def get(self, cups, period):
        interval = request.args.get('interval')
        try:
            interval = max(min(int(interval), 12), 1)
        except:
            interval = 12
        end = datetime.strptime(period, '%Y%m') + relativedelta(months=1)
        start = end - relativedelta(months=interval)
        current_app.logger.debug('CCH from {} to {}'.format(start, end))
        search_query = {
            'name': {'$regex': '^{}'.format(cups[:20])},
            'datetime': {'$gte': start, '$lt': end}
        }
        p1_search_query = {
            'name': {'$regex': '^{}'.format(cups[:20])},
            'datetime': {'$gte': start, '$lt': end},
            'type': P1_CURVE_TYPE
        }
        cursor_f5d = self.get_cursor_db(collection='tg_cchfact', query=search_query)
        cursor_f1 = self.get_cursor_db(collection='tg_f1', query=search_query)
        cursor_p1 = self.get_cursor_db(collection='tg_p1', query=p1_search_query)

        result = []
        if self._query_result_length(cursor_f5d) > 0:
            result = [self._curve_value(curve, WATT) for curve in cursor_f5d]
        elif self._query_result_length(cursor_f1) > 0 \
                or self._query_result_length(cursor_p1) > 0:
            result = self.ordered_merge(cursor_f1, cursor_p1)

        return Response(json.dumps(result), mimetype='application/json')


resources = [
    (CCHFact, '/CCHFact/<cups>/<period>')
]
