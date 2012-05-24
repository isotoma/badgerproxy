# Copyright 2012 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import shelve
import datetime


from twisted.application.service import Service
from twisted.internet import task
from twisted.python import log


class Resolver(Service):

    interval = 60 * 5

    def __init__(self, cachepath):
        self.domains = shelve.open(cachepath)
        self.refresh_ips()
        self._expire_task = task.LoopingCall(self.expire)

    def lookup(self, domain):
        # All IP addresses are whitelisted if one of their domains are whitelisted.
        if domain in self.ips:
            return domain
        ip = self.domains.get(domain, ('',''))[0]
        if ip:
            return ip
        return None

    def refresh_ips(self):
        self.ips = set(ip for ip,expire in self.domains.values())

    def add_domain(self, domain, ip, ttl):
        delta = datetime.timedelta(0, ttl, 0)
        expires = datetime.datetime.now() + delta
        log.msg("Adding '%s' -> %s, will expire at %s" % (domain, ip, expires))
        self.domains[domain] = (ip, expires)
        self.refresh_ips()

    def remove_domain(self, domain):
        log.msg("Removing domain entry for: '%s'" % domain)
        del self.domains[domain]
        self.ips = set(self.domains.values())
        self.refresh_ips()

    def expire(self):
        now = datetime.datetime.now()
        for k, v in self.domains.items():
            if v[1] < now:
                self.remove_domain(k)

    def startService(self):
        Service.startService(self)
        self._expire_task.start(self.interval, now=True)

    def stopService(self):
        Service.stopService(self)
        if self._expire_task.running:
            self._expire_task.stop()

