

class DynamoBackedObject:

    def __init__(self, _id):

        self.id = _id
        self.savers = {'id': None}

    def register_saver(self, var_name, saver=None):
        self.savers[var_name] = saver

    @classmethod
    def from_dict(cls, item, *args):
        """
        Parses mongo data and creates object
        """
        try:
            obj = cls(item['id'], *args)
        except KeyError:
            raise KeyError("Must provide an id key when instantiating \
                           a dynamo object")
        for key, value in item.items():
            if key == 'id':
                continue
            setattr(obj, key, value)
        return obj

    def save(self, table):
        """
        Saves this to dynamodb
        """
        item = {}
        print(self.savers.items())
        for var_name, saver in self.savers.items():
            if saver:
                print("Saver: ", saver)
                item = saver(item)
            else:
                item[var_name] = getattr(self, var_name)
        table.put_item(Item=item)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            equal = True
            for var in self.savers.keys():
                if var == 'id':
                    continue
                equal &= getattr(self, var) == getattr(other, var)
            return equal
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))
