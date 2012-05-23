
from twisted.internet.protocol import ClientFactory, Protocol

class PassthruProtocol(Protocol):

    def __init__(self, request):
        self.request = request

    def connectionMade(self):
        self.request.channel._registerSadface(self)
        self.request.setResponseCode(200, 'Connected')
        self.request.write('')

    def dataReceived(self, data):
        self.request.channel.transport.write(data)


class PassthruFactory (ClientFactory):

    def __init__(self, request):
        self.request = request

    def buildProtocol(self, addr):
        return PassthruProtocol(self.request)

    def clientConnectionFailed(self, connector, reason):
        self.request.setResponseCode(501, 'Gateway error')
        self.request.finish()

