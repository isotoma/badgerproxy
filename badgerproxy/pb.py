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

from optparse import OptionParser

from zope.interface import implements

from twisted.spread import pb
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.internet import reactor
from twisted.cred.credentials import UsernamePassword
from twisted.application import strports, service


class PbPerspective(pb.Avatar):

    def __init__(self, badgerproxy):
        self.badgerproxy = badgerproxy

    def perspective_add_dns(self, domain, ip, ttl):
        t = self.badgerproxy.resolver.add_domain(domain, ip, ttl)

    def logout(self):
        pass


class PbRealm(object):

    implements(IRealm)

    def __init__(self, badgerproxy):
        self.badgerproxy = badgerproxy

    def requestAvatar(self, avatarId, mind, *interfaces):
        if pb.IPerspective in interfaces:
            avatar = PbPerspective(self.badgerproxy)
            return pb.IPerspective, avatar, avatar.logout
        raise NotImplementedError("no interface")


class PbService(service.Service):

    def __init__(self, socket):
        service.Service.__init__(self)
        self.socket = socket

    def setServiceParent(self, parent):
        service.Service.__init__(self, parent)

        portal = Portal(PbRealm(parent))

        checker = InMemoryUsernamePasswordDatabaseDontUse()
        checker.addUser("guest", "guest")
        portal.registerChecker(checker)

        service = strports.service("unix:%s" % socket, pb.PBServerFactory(portal))
        service.setServiceParent(self)

