from __future__ import absolute_import

from flask.ext import login

from heman.config import mongo


login_manager = login.LoginManager()
"""Login manager object
"""


class APIUser(login.UserMixin):
    """API User object

    :param token: token for this user
    """
    def __init__(self, token, allowed):
        self.id = token
        self.allowed_contracts = allowed

    def is_authenticated(self):
        return True

    def get_id(self):
        return self.id

    def allowed(self, value, key='name'):
        return value in [x[key] for x in self.allowed_contracts]


@login_manager.header_loader
def load_user_from_header(header_val):
    header_val = header_val.replace('Basic ', '', 1)
    try:
        user, token = header_val.split()
        if user == 'token':
            res = mongo.db.tokens.find({'token': token})
            if res:
                res = res[0]
                return APIUser(res['token'], res.get('allowed_contracts', []))
    except Exception:
        return None


@login_manager.user_loader
def load_user(token):
    return APIUser(token)
