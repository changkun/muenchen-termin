# Copyright 2019 Changkun Ou. All rights reserved.
# Use of this source code is governed by a MIT
# license that can be found in the LICENSE file.

import re, json, requests, datetime, time

class Person:
    def __init__(self, name, birthday, email, salutation):
        self.name = name
        self.birthday = birthday
        self.email = email
        self.salutation = salutation

class TerminAutomation:
    def __init__(self, base_url, termin_type, person, date_start, date_end):
        # consts
        self.base_url = base_url
        self.termin_type = termin_type
        self.person = person
        self.desire_start = datetime.datetime.fromisoformat(date_start)
        self.desire_end = datetime.datetime.fromisoformat(date_end)

        # runtime configs
        self.__session = None
        self.__termin_type_key = None
        self.__termin_date = None
        self.__termine_time = None

    def get_termine(self):
        self.__session = requests.Session()
        self.__session.post(self.base_url)
        response = self.__session.post(self.base_url, {
            'CASETYPES[%s]' % self.termin_type: 1,
            'step': 'WEB_APPOINT_SEARCH_BY_CASETYPES',
        })
        try:
            json_str = re.search('jsonAppoints = \'(.*?)\'', response.text).group(1)
            return json.loads(json_str)
        except Exception as e:
            print('error: cannot find appointment, ', e)
            return {}

    # step 1: search for termine slot
    def found_termin(self):
        termin_dict = self.get_termine()
        if len(termin_dict.keys()) != 1:
            return False
        
        self.__termin_type_key = list(termin_dict.keys())[0]
        possibles = termin_dict[self.__termin_type_key]['appoints']
        valid_date = None

        # search time range
        delta = self.desire_end - self.desire_start
        for i in range(delta.days + 1):
            date_str = self.desire_start + datetime.timedelta(days=i)
            date_str = date_str.strftime('%Y-%m-%d')
            if date_str not in possibles:
                continue
            if len(possibles[date_str]) == 0:
                continue

            # return the earliest
            self.__termin_date = date_str
            self.__termine_time = possibles[date_str][0]

            print('found termin: %s, %s' % (self.__termin_date, self.__termine_time))

            return True

        return False

    # step 2: select desired termin slot
    def select_termin(self):
        if (self.__termin_type_key is None) or \
            (self.__termin_date is None) or \
            (self.__termine_time is None):
            print('error: termin search fail: ', 
                self.__termin_type_key, ' ', 
                self.__termin_date, ' ', 
                self.__termine_time)
            return

        response = self.__session.post(self.base_url, {
            'step': 'WEB_APPOINT_NEW_APPOINT',
            'APPOINT': '%s__%s__%s' % (self.__termin_type_key, 
                self.__termin_date, 
                self.__termine_time),
        })
        # print('debug step2: ', response.text)

    # step 3: book the appointment
    def book_termin(self):
        response = self.__session.post(self.base_url, {
            'step': 'WEB_APPOINT_SAVE_APPOINT',
            'CONTACT[salutation]': self.person.salutation,
            'CONTACT[name]': self.person.name,
            'CONTACT[birthday]': self.person.birthday,
            'CONTACT[email]': self.person.email,
            'CONTACT[privacy]': 1,
        })
        # print('debug step3: ', response.text)

class Config:
    def __init__(self, try_count, interval_second, base_url, termin_type, salutation, name, birthday, email, desire_start, desire_end):
        self.try_count = try_count
        self.interval_second = interval_second
        self.base_url = base_url
        self.termin_type = termin_type
        self.salutation = salutation
        self.name = name
        self.birthday = birthday
        self.email = email
        self.desire_start = desire_start
        self.desire_end = desire_end

    def valid(self):
        if (self.try_count is None) or (self.interval_second is None) or (self.base_url is None) or \
            (self.termin_type is None) or \
            (self.salutation is None) or \
            (self.name is None) or \
            (self.birthday is None) or \
            (self.email is None) or \
            (self.desire_start is None) or \
            (self.desire_end is None):
            return False
        return True

    @classmethod
    def from_json(cls, json_str):
        return cls(**json_str)

def main():
    with open('config.json', 'r') as f:
        conf = Config.from_json(json.load(f))

    if not conf.valid():
        print('error: config.json is invalid')
        return

    person = Person(conf.name, conf.birthday, conf.email, conf.salutation)
    service = TerminAutomation(
        conf.base_url, 
        conf.termin_type, 
        person, 
        conf.desire_start, 
        conf.desire_end
    )

    for i in range(1, conf.try_count):
        time.sleep(conf.interval_second) # search every seconds
        print('termin attempt %d start...' % i)
        if not service.found_termin():
            continue
        print('start book slot...')
        service.select_termin()
        service.book_termin()
        return
    print('cannot found termin.')

if __name__ == "__main__":
    main()