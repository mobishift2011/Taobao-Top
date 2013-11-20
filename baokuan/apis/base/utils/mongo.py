import re
import time

from mreplace import mreplace, int2str
from mongoengine.fields import StringField
from mongoengine.connection import get_db, DEFAULT_CONNECTION_NAME

class UniqueIDField(StringField):
    """ An Unique Id Field
   
    Ids are lowercase letters, 5-6 in length
    """
    def __init__(self, db_alias=None, *args, **kwargs):
        self.valid_pattern = re.compile(r'^[a-z]+$')
        self.collection_name = 'mongoengine.uniqueids'
        self.db_alias = db_alias or DEFAULT_CONNECTION_NAME
        return super(UniqueIDField, self).__init__(*args, **kwargs)

    def generate_new_value(self):
        sequence_name = self.owner_document._get_collection_name()
        sequence_id = "%s.%s" % (sequence_name, self.name)
        collection = get_db(alias=self.db_alias)[self.collection_name]
        counter = collection.find_and_modify(query={"_id": sequence_id},
                                             update={"$inc": {"next": 1}},
                                             new=True,
                                             upsert=True)
        intid = int(counter['next']) << 16 | int(time.time()) & 0xffff
        return mreplace(int2str(intid, 26))

    def __get__(self, instance, owner):

        if instance is None:
            return self

        if not instance._data:
            return

        value = instance._data.get(self.name)

        if not value and instance._initialised:
            value = self.generate_new_value()
            instance._data[self.name] = value
            instance._mark_as_changed(self.name)

        return value

    def __set__(self, instance, value):
        if value is None and instance._initialised:
            value = self.generate_new_value()
            instance._data[self.name] = value
        
        return super(UniqueIDField, self).__set__(instance, value)
    
    def validate(self, value):
        if not self.valid_pattern.match(value):
            self.error('Value should be all lower case alphabets')

    def to_python(self, value):
        if value is None:
            value = self.generate_new_value()
            self._data[self.name] = value
        return value


class IncludeUniqueIDField(object):
    id  =   UniqueIDField(primary_key=True) 
