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

from twisted.application.service import MultiService

from .pb import PbService
from .dns import Resolver
from .proxy import ProxyService

class BadgerProxy(MultiService):

    def __init__(self, config=None):
        MultiService.__init__(self)
        self.config = config

    def setServiceParent(self, parent):
        MultiService.setServiceParent(self, parent)

        self.pb = PbService(self.config['socket'])
        self.pb.setServiceParent(self)

        self.resolver = Resolver(self.config['resolver-cache'])
        self.resolver.setServiceParent(self)

        self.proxyservices = []
        for service in self.config['services']:
            p = ProxyService(service)
            p.setServiceParent(self)
            self.proxyservices.append(p)

