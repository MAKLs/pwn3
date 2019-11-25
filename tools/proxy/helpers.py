"""Constants and helper functions and classes.
"""
import re
from argparse import Action, ArgumentParser
from enum import Enum
from queue import Queue

MASTER_PORT = 3333
GAME_PORT_RANGE = (port for port in range(3000, 3005))
BUFSIZE = 4096
ENCODING = 'utf-8'
PACKET_QUEUE = Queue(-1)


class ConnectionType(Enum):
    """
    Types of possible proxy connections. Determines whether a connection's
    socket binds to a port and listens or attempts to connect to a host.
    """
    CLIENT = 1
    SERVER = 2


class ValidateHost(Action):
    """Verify host is a valid hostname or IP.
    """
    def __init__(self, *args, **kwargs):
        self.hostname_limit = 253
        self.label_limit = 63
        self.octet_limit = 255
        self.ip_pattern = re.compile(r'(\d+(\.|$)){4}', flags=re.IGNORECASE)
        self.hostname_pattern = re.compile(r'^([a-z0-9]+(\-[a-z0-9]*)*\.?)+$',
                                           flags=re.IGNORECASE)
        super().__init__(*args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            self._verify_host(values)
            setattr(namespace, self.dest, values)
        except ValueError as e:
            parser.error(str(e))

    def _verify_host(self, host: str):
        """Verify that the host is a valid IP address or hostname.

        Args:
            host (str): IP address or hostname to verify

        Raises:
            ValueError: value error is raised as soon as the host is determined
                to be invalid
        """
        # Handle IP addresses
        if re.match(self.ip_pattern, host):
            reconst_host = []
            octets = map(lambda o: int(o), host.split('.'))
            for o in octets:
                if o > self.octet_limit:
                    raise ValueError(f'Invalid octet {o} in IP address {host}')
                else:
                    reconst_host.append(str(o))
            if '.'.join(reconst_host) != host:
                raise ValueError(f'Remove extraneous 0s from IP address')
        # Handle hostnames
        elif re.match(self.hostname_pattern, host):
            hostname_len = 0
            for label in host.split('.'):
                label_len = len(label)
                if label_len > self.label_limit:
                    raise ValueError(f'Label {label} is too long ({label_len} vs. {self.label_limit} character max)')  # noqa: E501
                hostname_len += label_len + 1  # add 1 for delimitting '.'
            # Overcounted 1 delimitting '.'
            if hostname_len - 1 > self.hostname_limit:
                raise ValueError(f'Hostname {host} is too long ({hostname_len - 1} vs. {self.hostname_limit} character max)')  # noqa: E501
        else:
            raise ValueError(f'Host {host} is not a valid hostname or IP address')  # noqa: E501


def parser_factory(prog: str) -> ArgumentParser:
    parser = ArgumentParser(prog=prog)
    parser.add_argument('-d', '--destination-host', required=True,
                        type=str, action=ValidateHost,
                        help='Host to proxy data to')
    return parser
