# coding=utf-8
import json
import logging
import sys

from scrapy.http import Response
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

    def __init__(self, bucket, settings):
        self.bucket = bucket
        self.settings = settings

        # 获得access key和secret key
        self._access_key = settings.get('PIPELINE_QINIU_AK')
        self._secret_key = settings.get('PIPELINE_QINIU_SK')
        if not self._access_key or not self._secret_key:
            logging.getLogger('scrapy').error('PIPELINE_QINIU_AK or PIPELINE_QINIU_SK not specified.')
            raise NotConfigured

        self._bucket_mgr = None

    def get_file_stat(self, key):
        stat, error = self.bucket_mgr.stat(self.bucket, key)
        return stat

    def stat_file(self, key, info):
        def _onsuccess(stat):
            if stat:
                checksum = stat['hash']
                timestamp = stat['putTime'] / 10000000
                return {'checksum': checksum, 'last_modified': timestamp}
            else:
                return {}

        return threads.deferToThread(self.get_file_stat, key).addCallback(_onsuccess)

    def persist_file(self, path, buf, info, meta=None, headers=None):
        """
        因为我们采用七牛的fetch模型，所以，当request返回的时候，图像已经上传到了七牛服务器
        """
        pass

    def fetch_file(self, url, key):
        ret, error = self.bucket_mgr.fetch(url, self.bucket, key)
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
    """
    MEDIA_NAME = "file"
    DEFAULT_FILES_URLS_FIELD = 'file_urls'
    DEFAULT_FILES_RESULT_FIELD = 'files'

    def __init__(self, settings=None):
        """
        初始化
        :param settings:
        :return:
        """
        # 存放到哪个bucket中
        bucket = settings.get('PIPELINE_QINIU_BUCKET')
        if not bucket:
            logging.getLogger('scrapy').error('PIPELINE_QINIU_BUCKET not specified')
            raise NotConfigured
        self.store = QiniuFilesStore(bucket, settings)

        self.key_prefix = (settings.get('PIPELINE_QINIU_KEY_PREFIX') or '').strip()
        if not self.key_prefix:
            logging.getLogger('scrapy').error('PIPELINE_QINIU_KEY_PREFIX not specified')
            raise NotConfigured

        super(FilesPipeline, self).__init__(download_func=self.fetch)

    def fetch(self, request, spider):
        """download_func"""
        key = self.file_path(request)
        ret = self.store.fetch_file(request.url, key)

        return Response(request.url, body=json.dumps(ret))

    @classmethod
    def from_settings(cls, settings):
        if not settings.getbool('PIPELINE_QINIU_ENABLED', False):
            raise NotConfigured
        cls.FILES_URLS_FIELD = settings.get('FILES_URLS_FIELD', cls.DEFAULT_FILES_URLS_FIELD)
        cls.FILES_RESULT_FIELD = settings.get('FILES_RESULT_FIELD', cls.DEFAULT_FILES_RESULT_FIELD)
        cls.EXPIRES = settings.getint('FILES_EXPIRES', sys.maxint)

        return cls(settings=settings)

    def file_path(self, request, response=None, info=None):
        from scrapy.utils.request import request_fingerprint

        raw_key = request_fingerprint(request)
        return '%s%s' % (self.key_prefix, raw_key)

    def file_downloaded(self, response, request, info):
        return json.loads(response.body)['hash']
