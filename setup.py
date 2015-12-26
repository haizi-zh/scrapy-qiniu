# -*- coding: utf-8 -*-
from setuptools import setup
LONGDOC = """
scrapy_qiniu
=====

Scrapy中的media pipeline机制，可以方便地将静态资源资源（文件、图像等）下载到本地，然后进行处理。scrapy-qiniu扩展了这一机制，可以将资源存储到七牛云存储上面。并且，实现了以下几个特性：

* 支持缓存，可以避免静态资源的重复下载
* 采用fetch模式，让七牛服务器代为下载，而不用像默认的FilesPipeline那样，先下载到爬虫所在
主机，然后再上传到七牛服务器

"""

setup(name='scrapy_qiniu',
      version='0.1.2',
      description='Scrapy pipeline extension for qiniu.com',
      long_description=LONGDOC,
      author='Zephyre',
      author_email='haizi.zh@gmail.com',
      url='https://github.com/haizi-zh/scrapy-qiniu',
      license="MIT",
      classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: Chinese (Traditional)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Framework :: Scrapy',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Environment :: Console',
      ],
      keywords='crawler,spider,scrapy,qiniu',
      packages=['scrapy_qiniu'],
      install_requires=['Scrapy', 'qiniu'],
)
