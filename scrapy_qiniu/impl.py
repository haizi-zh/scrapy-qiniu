# coding=utf-8
import json
import logging
import sys

from scrapy.http import Response, Request
from scrapy.pipelines.files import FilesPipeline
from twisted.internet import threads
from qiniu import Auth, BucketManager
from scrapy.exceptions import NotConfigured

__author__ = 'zephyre'


class QiniuFilesStore(object):
    def get_access_key(self):
        return self._access_key

    def get_secret_key(self):
        return self._secret_key

    def get_bucket_mgr(self):
        if not self._bucket_mgr:
            ak = self.access_key
            sk = self.secret_key
            q = Auth(ak, sk)
            self._bucket_mgr = BucketManager(q)

        return self._bucket_mgr

    bucket_mgr = property(get_bucket_mgr)

    access_key = property(get_access_key)

    secret_key = property(get_secret_key)

    def __init__(self, settings):
        self.settings = settings

        # 获得access key和secret key
        self._access_key = settings.get('PIPELINE_QINIU_AK')
        self._secret_key = settings.get('PIPELINE_QINIU_SK')
        if not self._access_key or not self._secret_key:
            logging.getLogger('scrapy').error('PIPELINE_QINIU_AK or PIPELINE_QINIU_SK not specified.')
            raise NotConfigured

        self._bucket_mgr = None

    def get_file_stat(self, bucket, key):
        stat, error = self.bucket_mgr.stat(bucket, key)
        return stat

    def stat_file(self, path, info):
        def _onsuccess(stat):
            if stat:
                checksum = stat['hash']
                timestamp = stat['putTime'] / 10000000
                return {'checksum': checksum, 'last_modified': timestamp}
            else:
                return {}

        info = json.loads(path)
        return threads.deferToThread(self.get_file_stat, info['bucket'], info['key']).addCallback(_onsuccess)

    def persist_file(self, path, buf, info, meta=None, headers=None):
        """
        因为我们采用七牛的fetch模型，所以，当request返回的时候，图像已经上传到了七牛服务器
        """
        pass

    def fetch_file(self, url, key, bucket):
        if not bucket:
            logging.error('No bucket specified')
            raise IOError
        if not key:
            logging.error('No key specified')
            raise IOError

        ret, error = self.bucket_mgr.fetch(url, bucket, key)
        if ret:
            return ret
        else:
            raise IOError


class QiniuPipeline(FilesPipeline):
    """
    设置项：

    * PIPELINE_QINIU_ENABLED: 是否启用本pipeline
    * PIPELINE_QINIU_BUCKET: 存放在哪个bucket中
    * PIPELINE_QINIU_KEY_PREFIX: 资源在七牛中的key的名称为：prefix + hash(request.url)
    * QINIU_KEY_GENERATOR_FEILD: generator: 给定一个url, 如何获得资源在七牛中的bucket和key.
      该参数指明item中的哪个字段用来表示generator
    """
    MEDIA_NAME = "file"
    DEFAULT_FILES_URLS_FIELD = 'file_urls'
    DEFAULT_FILES_RESULT_FIELD = 'files'
    DEFAULT_QINIU_KEY_GENERATOR_FIELD = 'qiniu_key_generator'

    def __init__(self, settings=None):
        """
        初始化
        :param settings:
        :return:
        """
        # 存放到哪个bucket中
        bucket = settings.get('PIPELINE_QINIU_BUCKET')
        if not bucket:
            logging.getLogger('scrapy').warning('PIPELINE_QINIU_BUCKET not specified')
            raise NotConfigured
        self.bucket = bucket
        self.store = QiniuFilesStore(settings)

        self.key_prefix = (settings.get('PIPELINE_QINIU_KEY_PREFIX') or '').strip()
        if not self.key_prefix:
            logging.getLogger('scrapy').error('PIPELINE_QINIU_KEY_PREFIX not specified')
            raise NotConfigured

        super(FilesPipeline, self).__init__(download_func=self.fetch)

    def _extract_key_info(self, request):
        """
        从欲下载资源的request中, 获得资源上传七牛时的bucket和key
        """
        from scrapy.utils.request import request_fingerprint

        key_generator = request.meta.get('qiniu_key_generator')
        if key_generator:
            tmp = key_generator(request.url)
            bucket = tmp['bucket'] or self.bucket
            key = tmp['key']
        else:
            bucket = self.bucket
            key = '%s%s' % (self.key_prefix, request_fingerprint(request))

        return {'bucket': bucket, 'key': key}

    def fetch(self, request, spider):
        """download_func"""
        info = self._extract_key_info(request)

        ret = self.store.fetch_file(request.url, info['key'], info['bucket'])
        return Response(request.url, body=json.dumps(ret))

    def get_media_requests(self, item, info):
        """
        根据item中的信息, 构造出需要下载的静态资源的Request对象

        :param item:
        :param info:
        :return:
        """
        key_generator = item.get(self.QINIU_KEY_GENERATOR_FIELD)
        return [Request(x, meta={'qiniu_key_generator': key_generator}) for x in item.get(self.FILES_URLS_FIELD, [])]

    @classmethod
    def from_settings(cls, settings):
        if not settings.getbool('PIPELINE_QINIU_ENABLED', False):
            raise NotConfigured
        cls.FILES_URLS_FIELD = settings.get('FILES_URLS_FIELD', cls.DEFAULT_FILES_URLS_FIELD)
        cls.FILES_RESULT_FIELD = settings.get('FILES_RESULT_FIELD', cls.DEFAULT_FILES_RESULT_FIELD)
        cls.QINIU_KEY_GENERATOR_FIELD = settings.get('QINIU_KEY_GENERATOR_FIELD', cls.DEFAULT_QINIU_KEY_GENERATOR_FIELD)
        cls.EXPIRES = settings.getint('FILES_EXPIRES', sys.maxint)

        return cls(settings=settings)

    def file_path(self, request, response=None, info=None):
        """
        抓取到的资源存放到七牛的时候, 应该采用什么样的key? 返回的path是一个JSON字符串, 其中有bucket和key的信息
        """
        return json.dumps(self._extract_key_info(request))

    def file_downloaded(self, response, request, info):
        return json.loads(response.body)['hash']

    def item_completed(self, results, item, info):
        def process_result(result):
            data = json.loads(result['path'])
            result['bucket'] = data['bucket']
            result['key'] = data['key']
            return result

        if isinstance(item, dict) or self.FILES_RESULT_FIELD in item.fields:
            item[self.FILES_RESULT_FIELD] = [process_result(x) for ok, x in results if ok]
        return item
