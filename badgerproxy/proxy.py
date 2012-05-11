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

banner = """
<style>
HTML {
 padding-top: %(height)s;
 background: url('%(bannerurl)s') 0 0 repeat-x !important;
}
</style>
</head>
"""


def sibpath(asset):
    path = os.path.dirname(__file__)
    return os.path.join(path, asset)

class RewritingProxyClient(ProxyClient):
    def __init__(self, *args, **kwargs):
        ProxyClient.__init__(self, *args, **kwargs)
        self.rewrite = False
        self.length = None
        self.buffer = ''

    def sendHeader(self, name, value):
        log.msg(">>> %s: %s" % (name, value))
        if name.lower() == "accept-encoding":
            value = "identity"
        ProxyClient.sendHeader(self, name, value)

    def handleHeader(self, key, value):
        log.msg("<<< %s: %s" % (key, value))
        if key.lower() == "content-type":
            if value.startswith("text/html"):
                self.rewrite = True
            ProxyClient.handleHeader(self, key, value)
        elif key.lower() == "content-length":
            self.length = value
        else:
            ProxyClient.handleHeader(self, key, value)

    def handleEndHeaders(self):
        if not self.rewrite:
            if self.length:
                ProxyClient.handleHeader(self, "Content-Length", self.length)
            ProxyClient.handleEndHeaders(self)

    def handleResponsePart(self, buffer):
        if self.rewrite:
            self.buffer += buffer
        else:
            ProxyClient.handleResponsePart(self, buffer)

    def handleResponseEnd(self):
        log.msg("handleResponseEnd")
        if self.rewrite:
            banner2 = banner % dict(
                height = self.config['height'],
                bannerurl = self.config['bannerurl'],
                )
            buffer = self.buffer.replace("</head>", banner2)
            ProxyClient.handleHeader(self, "Content-Length", str(len(buffer)))
            ProxyClient.handleEndHeaders(self)
            ProxyClient.handleResponsePart(self, buffer)
            self.rewrite = False
        ProxyClient.handleResponseEnd(self)


class RewritingProxyClientFactory(ProxyClientFactory):
    protocol = RewritingProxyClient

    def buildProtocol(self, addr):
        log.msg("RewritingProxyClientFactory.buildProtocol")
        try:
            module, cls = self.root.config['rewriter']['cls'].split(":")
            protocol = getattr(__import__(module, fromlist=['blah']), cls)
        except KeyError:
            protocol = ProxyClient

        p = protocol(self.command, self.rest, self.version,
	            self.headers, self.data, self.father)

        p.factory = self
        p.root = self.root
        p.config = self.root.config['rewriter']

        return p

from twisted.internet import ssl
from twisted.protocols.tls import TLSMemoryBIOProtocol


from twisted.internet import reactor
from twisted.web.http import Request, HTTPChannel

class ReverseProxyRequest(Request):
    proxyClientFactoryClass = RewritingProxyClientFactory

    def __init__(self, channel, queued, reactor=reactor):
        Request.__init__(self, channel, queued)
        self.reactor = reactor

    def process(self):
        self.received_headers['host'] = self.channel.factory.host
        if 'accept' in self.received_headers:
            del self.received_headers['accept']

        clientFactory = self.proxyClientFactoryClass(
            self.method, self.uri, self.clientproto, self.getAllHeaders(),
            self.content.read(), self)

        clientFactory.root = self.channel.factory.root

        port = self.channel.factory.port
        host = self.channel.factory.host

        if port == 443:
            connect = self.reactor.connectSSL
            connect(host, port, clientFactory, ssl.ClientContextFactory())
        else:
            connect = self.reactor.connectTCP
            connect(host, port, clientFactory)



class ReverseProxy(HTTPChannel):
    requestFactory = ReverseProxyRequest


class TunnelProxyRequest (ProxyRequest):

    protocol = RewritingProxyClientFactory

    def process(self):
        if not self.channel.factory.root.is_method_allowed(self.method.upper()):
            self.setResponseCode(403, 'Forbidden method')
            self.finish()
            return

        if self.method.upper() == 'CONNECT':
            self._process_connect()
        else:
            return ProxyRequest.process(self)

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
        clientFactory = self.protocol(self.method, rest, self.clientproto, headers,
                               s, self)

        clientFactory.root = self.channel.factory.root

        self.reactor.connectTCP(host, port, clientFactory)

    def _process_connect(self):
        try:
            host, portStr = self.uri.split(':', 1)
            port = int(portStr)
        except ValueError:
            # Either the connect parameter is not HOST:PORT or PORT is
            # not an integer, in which case this request is invalid.
            self.setResponseCode(400)
            self.finish()
        else:
            #restrictedToPort = self.channel.factory.restrictedToPort
            #if (restrictedToPort is not None) and (port != restrictedToPort):
            if port != 443:
                self.setResponseCode(403, 'Forbidden port')
                self.finish()
            else:
                #self.reactor.connectTCP(host, port, TunnelProtocolFactory(self, host, port))

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


class TunnelProxy (Proxy):

    requestFactory = TunnelProxyRequest

    def __init__(self):
        self._tunnelproto = None
        Proxy.__init__(self)

    def _registerTunnel(self, tunnelproto):
        assert self._tunnelproto is None, 'Precondition failure: Multiple TunnelProtocols set: self._tunnelproto == %r; new tunnelproto == %r' % (self._tunnelproto, tunnelproto)
        self._tunnelproto = tunnelproto

    def dataReceived(self, data):
        if self._tunnelproto is None:
            Proxy.dataReceived(self, data)
        else:
            self._tunnelproto.dataReceived(data)


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


if __name__ == "__main__":
    from twisted.internet import reactor 
    from twisted.python import log 
    import sys 
    log.startLogging(sys.stdout) 
    reactor.listenTCP(8181, TunnelProxyFactory()) 
    reactor.run()

