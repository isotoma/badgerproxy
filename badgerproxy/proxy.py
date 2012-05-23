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

from twisted.application import service
from twisted.python import usage
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.web import http
from twisted.web.proxy import Proxy, ProxyRequest, ProxyClientFactory, ProxyClient
from twisted.web.proxy import ReverseProxy

from twisted.application import internet
from twisted.application import strports
from twisted.python import log

from StringIO import StringIO
import os
import urlparse

from .error import ForbiddenResponse
from .proxyclient import Proxier
from .internalproxy import InternalProxier
from .passthru import PassthruFactory

def sibpath(asset):
    path = os.path.dirname(__file__)
    return os.path.join(path, asset)

from twisted.internet import ssl
from twisted.protocols.tls import TLSMemoryBIOProtocol


from twisted.internet import reactor
from twisted.web.http import Request, HTTPChannel

class ReverseProxyRequest(Request):
    #proxyClientFactoryClass = RewritingProxyClientFactory

    def __init__(self, channel, queued, reactor=reactor):
        Request.__init__(self, channel, queued)
        self.reactor = reactor

    def process(self):
        host = self.received_headers['host'] = self.channel.factory.host
        port = self.channel.factory.port

        if 'accept' in self.received_headers:
            del self.received_headers['accept']

        p = Proxier(self.channel.factory.root, host, port)
        if not p.permitted():
            ForbiddenResponse(self, "You are not permitted to access this host").render()
            return

        if port == 443:
            proxy = p.proxy_ssl
        else:
            proxy = p.proxy

        proxy(self.method, self.uri, self.clientproto, self.getAllHeaders(), self.content.read(), self)



class ReverseProxy(HTTPChannel):
    requestFactory = ReverseProxyRequest


class TunnelProxyRequest (ProxyRequest):

    #protocol = RewritingProxyClientFactory

    def process(self):
        if not self.channel.factory.root.is_method_allowed(self.method.upper()):
            ForbiddenResponse(self, "You are not permitted to use this HTTP method").render()
            return

        if self.method.upper() == 'CONNECT':
            self._process_connect()
        else:
            self._process()

    def _process(self):
        parsed = urlparse.urlparse(self.uri)
        protocol = parsed[0]
        host = parsed[1]
        port = self.ports[protocol]
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        rest = urlparse.urlunparse(('', '') + parsed[2:])
        if not rest:
            rest = rest + '/'
        headers = self.getAllHeaders().copy()
        if 'host' not in headers:
            headers['host'] = host
        self.content.seek(0, 0)
        s = self.content.read()

        if host == "badger":
            P = InternalProxier
        else:
            P = Proxier

        p = P(self.channel.factory.root, host, port)
        if not p.permitted():
            ForbiddenResponse(self, "You are not permitted to access this host").render()
            return
        p.proxy(self.method, rest, self.clientproto, headers, s, self)

    def _process_connect(self):
        try:
            host, portStr = self.uri.split(':', 1)
            port = int(portStr)
        except ValueError:
            # Either the connect parameter is not HOST:PORT or PORT is
            # not an integer, in which case this request is invalid.
            self.setResponseCode(400)
            self.finish()
            return

        ip = self.channel.factory.root.parent.resolver.lookup(host)
        if not ip:
            ForbiddenResponse(self, "You are not permitted to access this host").render()
            return

        if port == 22:
            self.reactor.connectTCP(ip, port, PassthruFactory(self))
        elif port == 443:
            class FakeFactory:
                def log(self, meh):
                    pass
            FakeFactory.host = host
            FakeFactory.port = port
            FakeFactory.root = self.channel.factory.root
            rp = ReverseProxy()
            rp.factory = FakeFactory()

            contextFactory = ssl.DefaultOpenSSLContextFactory(sibpath('server.key'), sibpath('server.crt'))

            class FakeFactory2:
                _contextFactory = contextFactory
                _isClient = False
                def registerProtocol(self, meh):
                    pass
                def unregisterProtocol(self, meh):
                    pass
            ssl_rp = TLSMemoryBIOProtocol(FakeFactory2(), rp)

            self.channel._registerTunnel(ssl_rp)
            ssl_rp.makeConnection(self.transport)

            self.setResponseCode(200)
            self.write("")
        else:
            ForbiddenResponse(self, "You are not permitted to access this port").render()


class TunnelProxy (Proxy):

    requestFactory = TunnelProxyRequest

    def __init__(self):
        self._tunnelproto = None
        self._sadface = None
        Proxy.__init__(self)

    def _registerTunnel(self, tunnelproto):
        assert self._tunnelproto is None, 'Precondition failure: Multiple TunnelProtocols set: self._tunnelproto == %r; new tunnelproto == %r' % (self._tunnelproto, tunnelproto)
        self._tunnelproto = tunnelproto

    def _registerSadface(self, sadface):
        self._sadface = sadface

    def dataReceived(self, data):
        if self._tunnelproto:
            self._tunnelproto.dataReceived(data)
        elif self._sadface:
            self._sadface.transport.write(data)
        else:
            Proxy.dataReceived(self, data)


class TunnelProxyFactory (http.HTTPFactory):
    protocol = TunnelProxy

    def __init__(self, root):
        http.HTTPFactory.__init__(self)
        self.root = root


class ProxyService(service.MultiService):

    def __init__(self, config):
        service.MultiService.__init__(self)
        self.config = config

    def is_method_allowed(self, method):
        if not "methods" in self.config:
            return True
        methods = self.config["methods"]
        if "allowed" in method:
            if method in method["allowed"]:
                return True
            return False
        elif "blocked" in method:
            if method in method["blocked"]:
                return False
            return True
        return True

    def setServiceParent(self, parent):
        service.MultiService.setServiceParent(self, parent)

        s = strports.service(self.config['listen'], TunnelProxyFactory(self))
        s.setServiceParent(self)


