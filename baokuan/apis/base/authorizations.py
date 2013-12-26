from tastypie.authorization import Authorization
from tastypie.exceptions import Unauthorized


class UserAuthorization(Authorization):
    def create_detail(self, object_list, bundle):
        if bundle.request.user and bundle.request.user.is_authenticated():
            bundle.obj.user = bundle.request.user
            return True

        return False

    def delete_detail(self, object_list, bundle):
        raise Unauthorized("Sorry, no deletes.")