import os
import json
import asyncio
import urllib
from pathlib import Path
from itertools import repeat
from urllib.parse import urljoin

import singer
import requests
import pendulum
from singer.bookmarks import write_bookmark, get_bookmark
from pendulum import datetime, period
import datetime
from dateutil import relativedelta

LOGGER = singer.get_logger()

class PagerdutyAuthentication(requests.auth.AuthBase):
    def __init__(self, api_token: str):
        self.api_token = api_token

    def __call__(self, req):
        req.headers.update({"Authorization": " Token token=" + self.api_token})

        return req


class PagerdutyClient:
    def __init__(self, auth: PagerdutyAuthentication, url="https://api.pagerduty.com/"):
        self._base_url = url
        self._auth = auth
        self._session = None

    @property
    def session(self):
        if not self._session:
            self._session = requests.Session()
            self._session.auth = self._auth
            self._session.headers.update({"Accept": "application/json"})

        return self._session

    def _get(self, path, params=None):
        #url = urljoin(self._base_url, path)
        url = self._base_url + path
        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json()


    def incidents(self, state, config):
        try:
            bookmark = get_bookmark(state, "incidents", "since")
            query_base = f"incidents?limit=100&total=true&utc=true"
            if bookmark:
                start_date = datetime.datetime.strptime(bookmark, '%Y-%m-%dT%H:%M:%S.%f')
            else:
                start_date = datetime.datetime.strptime(config['start_date'], '%Y-%m-%d')
                #query += "&since=" + urllib.parse.quote(start_date) + '&until='+ datetime.datetime.utcnow().isoformat()
            r = relativedelta.relativedelta(datetime.datetime.utcnow(),start_date)
            result = {}
            if r.years > 0 or r.months >= 5:
                while r.years > 0 or r.months >= 5:
                    until = (start_date + datetime.timedelta(5*365/12))
                    query = query_base +  "&since=" + urllib.parse.quote(start_date.isoformat()) + "&utc=true" + "&until="+ urllib.parse.quote(until.isoformat())
                    incidents = self._get(query)
                    iterable = incidents
                    if 'incidents' in result:
                        result['incidents'].extend(iterable['incidents'])
                    else:
                        result = iterable
                    offset = 0
                    while iterable['more']:
                        offset = offset + result['limit']
                        query += "&offset=" + str(offset)
                        incidents = self._get(query)
                        iterable = incidents
                        result['incidents'].extend(iterable['incidents'])
                    start_date = until
                    r = relativedelta.relativedelta(datetime.datetime.utcnow(), start_date)
            query = query_base +  "&since=" + urllib.parse.quote(start_date.isoformat()) + '&until='+ urllib.parse.quote(datetime.datetime.utcnow().isoformat())
            incidents = self._get(query)
            iterable = incidents
            if 'incidents' in result:
                result['incidents'].extend(iterable['incidents'])
            else:
                result = iterable
            offset = 0
            while iterable['more']:
                offset = offset + result['limit']
                query += "&offset=" + str(offset)
                incidents = self._get(query)
                iterable = incidents
                result['incidents'].extend(iterable['incidents'])
            return result
        except Exception as e:
            LOGGER.error(e)
            return None

    def getAll(self, stream):
        try:
            query = f"{stream}?limit=100&total=true"
            result = self._get(query)
            iterable = result
            offset = 0
            while iterable['more']:
                offset = offset + iterable['limit']
                query += "&offset=" + str(offset)
                iterable = self._get(query)
                result[stream].extend(iterable[stream])
            return result
        except:
            return None

class PagerdutySync:
    def __init__(self, client: PagerdutyClient, state={}, config={}):
        self._client = client
        self._state = state
        self._config = config
        self._incidents = self.client.incidents(state, config)

    @property
    def client(self):
        return self._client

    @property
    def state(self):
        return self._state

    @property
    def config(self):
        return self._config

    @state.setter
    def state(self, value):
        singer.write_state(value)
        self._state = value

    def sync(self, stream, schema):
        func = getattr(self, f"sync_{stream}")
        return func(schema)

    async def sync_incidents(self, schema):
        """Incidents."""
        stream = "incidents"
        loop = asyncio.get_event_loop()

        singer.write_schema(stream, schema, ["id"])
        self._incidents = await loop.run_in_executor(None, self.client.incidents, self.state, self.config)
        if self._incidents:
            for incident in self._incidents['incidents']:
                singer.write_record(stream, incident)
            self.state = write_bookmark(self.state, stream, "since", datetime.datetime.utcnow().isoformat(timespec='milliseconds'))

    async def sync_alerts(self, schema, period: pendulum.period = None):
        """Alerts per incidents."""
        stream = "alerts"
        loop = asyncio.get_event_loop()

        singer.write_schema(stream, schema, ["id"])
        #incidents = await loop.run_in_executor(None, self.client.incidents, self.state, self.config)
        if self._incidents:
            for incident in self._incidents['incidents']:
                query = 'incidents/' + incident['id'] + "/alerts"
                alerts = await loop.run_in_executor(None, self.client.getAll, query)
                if (alerts):
                    for alert in alerts['alerts']:
                        singer.write_record(stream, alert)


    async  def sync_services(self, schema, period: pendulum.period = None):
        """All Services."""
        stream = "services"
        loop = asyncio.get_event_loop()

        singer.write_schema(stream, schema, ["id"])
        services = await loop.run_in_executor(None, self.client.getAll, 'services')
        if services:
            for service in services['services']:
                singer.write_record(stream, service)

    async def sync_escalation_policies(self, schema):
        """All Escalation Policies."""
        stream = "escalation_policies"
        loop = asyncio.get_event_loop()

        singer.write_schema(stream, schema, ["id"])
        policies = await loop.run_in_executor(None, self.client.getAll, 'escalation_policies')
        if policies:
            for policie in policies['escalation_policies']:
                singer.write_record(stream, policie)

    async def sync_teams(self, schema):
        """All Teams."""
        stream = "teams"
        loop = asyncio.get_event_loop()
        singer.write_schema(stream, schema, ["id"])
        teams = await loop.run_in_executor(None, self.client.getAll, 'teams')
        if teams:
            for team in teams['teams']:
                singer.write_record(stream, team)

    async def sync_users(self, schema):
        """All Users."""
        stream = "users"
        loop = asyncio.get_event_loop()
        singer.write_schema(stream, schema, ["id"])
        users = await loop.run_in_executor(None, self.client.getAll, 'users')
        if users:
            for user in users['users']:
                singer.write_record(stream, user)

    async def sync_vendors(self, schema):
        """All Vendors."""
        stream = "vendors"
        loop = asyncio.get_event_loop()
        singer.write_schema(stream, schema, ["id"])
        vendors = await loop.run_in_executor(None, self.client.getAll, 'vendors')
        if vendors:
            for vendor in vendors['vendors']:
                singer.write_record(stream, vendor)