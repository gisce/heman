import json
import pymongo

from flask import current_app, jsonify, Response

from heman.api import AuthorizedResource
from heman.auth import check_contract_allowed
from heman.config import mongo


class InfoenergiaResource(AuthorizedResource):
    method_decorators = (
        AuthorizedResource.method_decorators + [check_contract_allowed]
    )

    def options(self, *args, **kwargs):
        return jsonify({})

    def get_last_infoenergia_report(self, contract_name):
        return mongo.db['infoenergia_reports'].find_one(
            {'contractId': contract_name},
            sort=[('months', pymongo.ASCENDING)]
        )


class InfoenergiaReport(InfoenergiaResource):

    def get(self, contract):
        current_app.logger.debug('Infoenergia Report, contract {}'.format(contract))

        infoenergia_report = self.get_last_infoenergia_report(contract_name=contract)

        if infoenergia_report:
            return Response(json.dumps(infoenergia_report), mimetype='application/json')

        return Response({}, mimetype='application/json')




resources = [
    (InfoenergiaReport, '/InfoenergiaReport/<contract>')
]
