import json


class KeyManager:
    def __init__(self, store):
        self.store = store
        self.keys = []
        self.__load()

    def __save(self):
        with open(self.store, 'w') as outfile:
            json.dump(self.keys, outfile)

    def __load(self):
        try:
            with open(self.store, 'r') as infile:
                self.keys = json.load(infile)
        except FileNotFoundError:
            self.keys = []

    def add(self, api_key, vcode, char_id, name, email):
        self.keys.append((api_key, vcode, char_id, name, email))
        self.__save()

    def remove(self, index):
        self.keys.pop(index)
        self.__save()
