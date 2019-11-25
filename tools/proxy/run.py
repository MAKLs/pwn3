"""Entry point to run proxy server
"""
import helpers
from proxy import ProxyServer

if __name__ == '__main__':
    args = helpers.parser_factory(__file__).parse_args()
    proxies = []

    # Set up proxy for master server
    master_proxy = ProxyServer('0.0.0.0', args.destination_host,
                               helpers.MASTER_PORT)
    master_proxy.start()

    # Set up proxy for each possible game server instance
    for port in helpers.GAME_PORT_RANGE:
        game_proxy = ProxyServer('0.0.0.0', args.destination_host, port)
        game_proxy.start()
