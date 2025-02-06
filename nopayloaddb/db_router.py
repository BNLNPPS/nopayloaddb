import random
from nopayloaddb.middleware import get_current_request

class ReadWriteRouter:
    def db_for_read(self, model, **hints):
        """Route read queries to one of the read databases."""
        # Redirect everything to default
        #db = random.choice(['read_db_1', 'read_db_2'])
        # Check if request information is available
        #request = get_current_request()
        #if request and request.method == 'GET':
        #        return db
        return 'default'

    def db_for_write(self, model, **hints):
        """Route write queries to the default database."""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if both objects are in the same database."""
        db_set = {'default', 'read_db_1', 'read_db_2'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on the default database."""
        return db == 'default'
