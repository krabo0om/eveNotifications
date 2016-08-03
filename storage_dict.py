import json
import os

import sys


class StorageDictList:
    """
    backed up by a file this dict allows adding and removing values associated with a single key
    """

    def __init__(self, store):
        """
        creates a new store, tries to load from file
        :param store: where to load data from
        """
        self.data = dict()
        self.store = store
        self.__load()

    def __load(self):
        try:
            with open(self.store, 'r') as infile:
                self.data = json.load(infile)
        except FileNotFoundError:
            self.data = {}

    def __save(self):
        tmp = {}    # convert set into a list
        for k in self.data:
            tmp[k] = list(self.data[k])
        with open(self.store, 'w') as outfile:
            json.dump(tmp, outfile)

    def add(self, key, value):
        """
        adds the value to the list associated with the key
        :param key: the unique key
        :param value: a value to add
        """
        try:
            values = set(self.data[key])
        except KeyError:
            values = set()
        values.add(value)
        self.data[key] = values
        self.__save()

    def remove(self, key, value):
        """
        removes a value from the list associated the unique key
        :param key: the unique key
        :param value: the value to remove
        """
        try:
            self.data[key].remove(value)
            self.__save()
        except (KeyError, ValueError):
            pass

    def contains(self, key, value):
        """
        checks if the value is already associated with the key
        @param key: the unique key
        @param value: the value to check
        @return: True if value is already present
        """
        try:
            return value in self.data[key]
        except KeyError:
            return False