import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.adapter import MeasuredAdapter


def test_pool_reuses_connection_and_baseline_does_not():
    """Servidor HTTP local de prueba; no es una medición de un motor real."""
    ports = []
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def do_GET(self):
            ports.append(self.client_address[1])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'[]')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        for mode in ('baseline', 'pooled'):
            adapter = MeasuredAdapter(f'http://127.0.0.1:{server.server_port}', mode)
            try:
                assert adapter.query_sql('SELECT 1') == []
                assert adapter.query_sql('SELECT 1') == []
            finally:
                adapter.close()
        assert ports[0] != ports[1]
        assert ports[2] == ports[3]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
