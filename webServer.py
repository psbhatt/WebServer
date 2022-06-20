import http.server as s
import os
import subprocess



class BaseCase(object):
    """Parent for case handlers."""

    @staticmethod
    def handle_file(handler, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            handler.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(full_path, msg)
            handler.handle_error(msg)

    @staticmethod
    def index_path(handler):
        return os.path.join(handler.full_path, 'index.html')

    @staticmethod
    def test(handler):
        assert False, 'Not implemented.'

    @staticmethod
    def act(handler):
        assert False, 'Not implemented.'


class CaseCGIFile(BaseCase):
    """Something runnable."""
    @staticmethod
    def test(handler):
        return os.path.isfile(handler.full_path) and \
               handler.full_path.endswith('.py')

    @staticmethod
    def act(handler):
        handler.run_cgi(handler.full_path)


class CaseDirectoryIndexFile(BaseCase):
    """Serve index.html page for a directory."""

    @staticmethod
    def index_path(handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               os.path.isfile(self.index_path(handler))

    def act(self, handler):
        handler.handle_file(self.index_path(handler))


class CaseDirectoryNoIndexFile(BaseCase):
    """Serve listing for a directory without an index.html page."""
    @staticmethod
    def index_path(handler):
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        return os.path.isdir(handler.full_path) and \
               not os.path.isfile(self.index_path(handler))

    @staticmethod
    def act(handler):
        handler.list_dir(handler.full_path)


class CaseNoFile(BaseCase):
    """File or directory does not exist."""

    @staticmethod
    def test(handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise Exception("'{0}' not found".format(handler.path))


class CaseExistingFile(BaseCase):
    """File exists."""
    @staticmethod
    def test(handler):
        return os.path.isfile(handler.full_path)

    @staticmethod
    def act(handler):
        handler.handle_file(handler.full_path)


class CaseAlwaysFail(BaseCase):
    """Base case if nothing else worked."""
    @staticmethod
    def test(handler):
        return True

    def act(self, handler):
        raise Exception("Unknown object '{0}'".format(handler.path))


class RequestHandler(s.BaseHTTPRequestHandler):
    Cases = [CaseNoFile(),
             CaseCGIFile(),
             CaseExistingFile(),
             CaseDirectoryIndexFile(),
             CaseDirectoryNoIndexFile(),
             CaseAlwaysFail()]
    Page = '''\
<html>
<body>
<table>
<tr>  <td>Header</td>         <td>Value</td>          </tr>
<tr>  <td>Date and time</td>  <td>{date_time}</td>    </tr>
<tr>  <td>Client host</td>    <td>{client_host}</td>  </tr>
<tr>  <td>Client port</td>    <td>{client_port}s</td> </tr>
<tr>  <td>Command</td>        <td>{command}</td>      </tr>
<tr>  <td>Path</td>           <td>{path}</td>         </tr>
</table>
</body>
</html>
'''
    Error_Page = """\
           <html>
           <body>
           <h1>Error accessing {path}</h1>
           <p>{msg}</p>
           </body>
           </html>
           """

    def do_GET(self):
        try:
            self.full_path = os.getcwd() + self.path

            # Figure out how to handle it.
            for case in self.Cases:
                if case.test(self):
                    case.act(self)
                    break

            # Handle errors.
        except Exception as msg:
            self.handle_error(msg)

    # def handle_file(self, full_path):
    #     try:
    #         with open(full_path, 'rb') as reader:
    #             content = reader.read()
    #         self.send_content(content)
    #     except IOError as msg:
    #         msg = "'{0}' cannot be read: {1}".format(self.path, msg)
    #         self.handle_error(msg)

    # Handle unknown objects.
    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg)
        self.send_content(content, 404)

    # Send actual content.
    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if isinstance(content, str):
            self.wfile.write(content.encode("utf-8"))
        elif isinstance(content, bytes):
            self.wfile.write(content)

    Listing_Page = '''\
            <html>
            <body>
            <ul>
            {0}
            </ul>
            </body>
            </html>
            '''

    def list_dir(self, full_path):
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e)
                       for e in entries if not e.startswith('.')]
            page = self.Listing_Page.format('\n'.join(bullets))
            self.send_content(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(self.path, msg)
            self.handle_error(msg)

    def run_cgi(self, full_path):
        cmd = ["python3", full_path]
        child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        data = child.stdout.read()
        self.send_content(data)


if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = s.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()
