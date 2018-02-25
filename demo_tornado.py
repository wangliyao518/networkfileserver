# -*- coding: utf-8 -*- 
from tornado import web, ioloop, httpserver, gen
from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import run_on_executor
#from urllib.parse import quote  # 下载文件时提供中文文件名编码
from urllib import pathname2url as quote
import time, os

filepath = "upload"
host = "http://127.0.0.1"
port = 8888


def fsizestr(size):
    if (size < 1024):
        return "{:d}Bytes".format(size)
    if (size < 1024 * 1024):
        return "{:.2f}KB".format(size / 1024)
    if (size < 1024 * 1024 * 1024):
        return "{:.2f}M".format(size / (1024 * 1024))
    return "{:.2f}G".format(size / (1024 * 1024 * 1024))


class PgMain(web.RequestHandler):
    def get(self, *args, **kwargs):
        self.redirect('/catalog')


class PgCatalog(web.RequestHandler):
    executor = ThreadPoolExecutor(10)

    @run_on_executor()
    def get(self, *args, **kwargs):
        catalogrec = []
        for frec in os.listdir(filepath):
            info = os.stat(os.path.join(filepath, frec))
            catalogrec.append({'fname': frec, 'fsize': fsizestr(info.st_size),
                               'ftime': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.st_ctime)),
                               'url': "{:s}:{:d}/getfile?fn={:s}".format(host, port, frec),
                               'delurl': "{:s}:{:d}/delfile?fn={:s}".format(host, port, frec)})
        self.render('tornado_pan.html', **{"catalogrec": catalogrec})


class PgUpload(web.RequestHandler):
    executor = ThreadPoolExecutor(10)

    @run_on_executor()
    def post(self):
        fds = self.request.files.get('myuploadfile', None)  # 提取表单中‘name’为‘myuploadfile’的文件元数据
        if fds:
            for fd in fds:
                filename = fd['filename']
                file_path = os.path.join(filepath, filename)
                with open(os.path.join(filepath, fd['filename']), 'wb') as f:
                    f.write(fd['body'])
                print("上传文件：", fd['filename'])
        self.redirect('/catalog')


class PgGetfile(web.RequestHandler):
    executor = ThreadPoolExecutor(10)

    @run_on_executor()
    def get(self):
        # get_argument(self, name, default=_ARG_DEFAULT, strip=True)方法可以设置默认值，也可以设置是否删除两端的空格。
        # get_arguments(self, name, strip=True)
        fn = self.get_argument('fn')
        if not fn:
            self.redirect('/catalog')
            return
        if os.path.isfile(os.path.join(filepath, fn)):
            print("!下载：", fn)
            self.set_header('Content-Type', 'application/octet-stream')  # Content-Type可以根据实际情况
            self.set_header('Content-Disposition',
                            'attachment; filename=' + quote(fn) + "; filename*=utf-8''{}".format(quote(fn)))
            with open(os.path.join(filepath, fn), 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    self.write(data)
            self.finish()
            return
        self.send_error(404)


class PgDelfile(web.RequestHandler):
    def get(self):
        fn = self.get_argument('fn')
        if fn and os.path.isfile(os.path.join(filepath, fn)):
            print("!删除：", fn)
            os.remove(os.path.join(filepath, fn))
        self.redirect('/catalog')


setting = {
    'template_path': 'template',
    'static_path': 'static',
    'debug': True,
}

app = web.Application([
    ('/', PgMain),
    ('/catalog', PgCatalog),
    ('/upload', PgUpload),
    ('/getfile', PgGetfile),
    ('/delfile', PgDelfile),
], **setting)

# web服务启动
if __name__ == "__main__":
    my_http_server = httpserver.HTTPServer(app)
    my_http_server.listen(port)
    ioloop.IOLoop.current().start()
