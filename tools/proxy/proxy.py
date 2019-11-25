"""Classes for proxying data between two hosts.
"""
import importlib
import math
import parser
import socket
import threading
import time

import helpers


class ProxyConnection(threading.Thread):
    """Generic conection class for a proxy server.

    Used to:
        * Parse packets to and from PwnAdventure 3 game servers into
            human-readable messages
        * Inject exploitative packets into client->server stream

    Depending on the ConnectionType it is initialized with, it may behave
    as the client->server connection or server->client connect.
    """
    def __init__(self, host: str, port: int,
                 conn_type: helpers.ConnectionType = helpers.ConnectionType.SERVER,  # noqa: E501
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self._conn_event = threading.Event()
        self._retries = 0
        self._sock = None
        self._conn_type = conn_type
        self._dest_conn = None
        self.host = host
        self.port = port
        self.name = f'{self.port}'

    @property
    def conn_type(self) -> helpers.ConnectionType:
        return self._conn_type

    @property
    def dest_conn(self) -> 'ProxyConnection':
        return self._dest_conn

    @dest_conn.setter
    def dest_conn(self, conn: 'ProxyConnection'):
        assert isinstance(conn, ProxyConnection), \
               'Proxy.dest_conn must be another proxy connection'
        self._dest_conn = conn

    @property
    def retry_interval(self):
        return 20 * (1 / (1 + math.e**(-self._retries / 10)) - 0.4)

    def is_running(self) -> bool:
        """Determine whether connection should continue proxying data.

        If either client or server close connection, proxying should stop.

        Returns:
            bool: True if connection should still proxy data, else False
        """
        return not self._stop_event.is_set()

    def _listen(self, sock: socket.socket):
        """Open up a listener for a client to connect to.

        Args:
            sock (socket.socket): connection to client
        """
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(1)
        self._sock, _ = sock.accept()

    def _connect(self, sock: socket.socket):
        """Connect to host.

        Args:
            sock (socket.socket): connection to server
        """
        # No reason to connect to server until client has... wait
        self.dest_conn.await_conn()
        self._sock = sock
        # Try to connect to server indefinitely
        connected = False
        while not connected:
            try:
                self._sock.connect((self.host, self.port))
                connected = True
            except ConnectionRefusedError:
                print(f'Connection refused... retrying in {self.retry_interval} seconds')  # noqa: E501
                time.sleep(self.retry_interval)
            finally:
                self._retries += 1

    def await_conn(self):
        """Block thread until a connection event is received.
        """
        self._conn_event.wait()

    def open(self):
        """Wrapper to open a connection for SERVER or CLIENT connections.

        For client connections, a listener is opened and awaits a connection.
        Server connections will wait until the corresponding listener receives
        a connection and then connects to the host.

        Raises:
            Exception: only SERVER and CLIENT connection types are supported.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.conn_type is helpers.ConnectionType.CLIENT:
            self._listen(sock)
        elif self.conn_type is helpers.ConnectionType.SERVER:
            self._connect(sock)
        else:
            raise Exception(f'Unknown connection type: {self.conn_type}')
        # Signal that this thread has successfully opened a connection
        self._conn_event.set()
        print(f'[{self.getName()}] New connection: {self.host}:{self.port}')

    def stop(self):
        """Close both the source and destination connections.

        First, the source connection is closed. Then, a stop event is sent to
        the current thread. Finally, the destination connection is called to
        stop.
        """
        try:
            # Close socket
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except OSError as ose:
            # Socket was already closed on other end
            print(f'[{self.getName()}] Stop error - {ose}')
        finally:
            # Send a stop event to this thread
            self._stop_event.set()
            # If the destination connection is still running, stop that too
            if self.dest_conn.is_running():
                self.dest_conn.stop()

    def send(self, data: bytes):
        """Send a buffer of data to the destination connection.

        Args:
            data (bytes): payload to proxy to destination
        """
        # Wait for destination to be connected before sending anything
        self.dest_conn.await_conn()
        try:
            self.dest_conn._sock.sendall(data)
        except OSError as ose:
            # Desntination socket is closed. No reason to continue
            print(f'[{self.getName()}] Send error - {ose}')
            self.stop()

    def receive(self) -> bytes:
        """Fetch data buffer from source socket.

        Blocks until buffer is received.

        Returns:
            bytes: buffer received by connection to be proxied
        """
        return self._sock.recv(helpers.BUFSIZE)

    def run(self):
        """Main run loop for connection.
        """
        # Open up connection
        self.open()
        while self.is_running():
            data = self.receive()
            self.send(data)
            if data == b'':
                # Source wants to close... stop the connection
                self.stop()
            else:
                # Try to parse the payload
                try:
                    importlib.reload(parser)
                    parser.parse(data, self.port, self.conn_type)
                except Exception as e:
                    print('Failed parse data', f'Reason: {e}', f'Data: {data}',
                          sep='\n\t')
            # Send data from server packet
            # TODO: consider sending async, since these are injected packets
            if self.conn_type == helpers.ConnectionType.CLIENT:
                try:
                    packet = helpers.PACKET_QUEUE.get_nowait()
                    self.send(packet)
                    helpers.PACKET_QUEUE.task_done()
                except Exception:
                    # TODO: catch empty exception from get_nowait()
                    pass
        print(f'[{self.getName()}] - exiting run loop')


class ProxyServer(threading.Thread):
    """Class to proxy data between two hosts over ProxyConnection objects.
    """
    def __init__(self, src_host: str, dest_host: str, port: int,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.src_host = src_host
        self.dest_host = dest_host
        self.port = port

    def is_running(self) -> bool:
        """Determine whether server should continue running

        Returns:
            bool: True if server should continue to run, else False
        """
        return not self._stop_event.is_set()

    def run(self):
        """Main run loop for server.
        """
        # TODO close proxy gracefully on Ctrl-C
        print(f'Staring proxy for {self.src_host} <-> {self.dest_host} over port {self.port}')  # noqa: E501
        while self.is_running():
            # Open listener to proxy client data & broker to proxy server data
            listener = ProxyConnection(self.src_host, self.port,
                                       helpers.ConnectionType.CLIENT,
                                       daemon=True)
            broker = ProxyConnection(self.dest_host, self.port,
                                     helpers.ConnectionType.SERVER,
                                     daemon=True)
            # Hook up listener and broker as each other's sink
            broker.dest_conn = listener
            listener.dest_conn = broker
            # Fire them up and wait until they close
            listener.start()
            broker.start()
            listener.join()
            broker.join()
