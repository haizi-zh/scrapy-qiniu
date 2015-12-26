# scrapy-qiniu

Scrapy中的media pipeline机制，可以方便地将静态资源资源（文件、图像等）下载到本地，然后进行处理。scrapy-qiniu扩展了这一机制，可以将资源存储到七牛云存储上面。并且，实现了以下几个特性：

* 支持缓存，可以避免静态资源的重复下载
* 采用fetch模式，让七牛服务器代为下载，而不用像默认的FilesPipeline那样，先下载到爬虫所在
主机，然后再上传到七牛服务器  

关于Scrapy的media pipeline机制，请参阅[这里](http://doc.scrapy.org/en/latest/topics/media-pipeline.html)。

## Installation

```bash
pip install scrapy-qiniu
```

## Usage

### Getting started

首先，需要在settings中启用本pipeline:

```python
ITEM_PIPELINES = {
  'scrapy_qiniu.QiniuPipeline': 10
}
```

注意，`QiniuqPipeline`的优先级最好要高于普通的pipeline。

然后，在运行爬虫的时候，需要设置好以下Settings项目：

* PIPELINE_QINIU_ENABLED: 是否启用本pipeline（如果将本设置项置为1，将启用本pipeline）
* PIPELINE_QINIU_BUCKET: 存放在哪个bucket中
* PIPELINE_QINIU_KEY_PREFIX: 资源在七牛中的key的名称为：`prefix + hash(request.url)`

最后，在抓取到网页，构造item的时候，假设需要抓取这两个网址：

`http://www.foo.com/bar-1.jpg`和`http://www.foo.com/bar-2.jpg`

可以这么做：

```python
item['file_urls'] = ['http://www.foo.com/bar-1.jpg', 'http://www.foo.com/bar-2.jpg']
```

这样一来，`QiniuPipeline`会自动将这两个资源上传到七牛服务器上，并且在返回的item中，将资源上传的结果添加到`files`字段中：

```python
{
  "key": "your_key",
  "bucket": "your_bucket",
  "checksum": "FpSAj-vs1tGIcQ5qF6PsJku2_sPa",
  "url": "http://www.foo.com/bar.jpg",
  "path": "the_path_string"
}
```

### Advanced usage

如果需要更加细颗粒度地控制静态资源的上传，可以指定item中的`qiniu_key_generator`属性。这是一个函数对象，它接收一个url，并返回bucket名称和key的取值。`QiniuPipeline`根据此结果，进行静态资源的下载和保存工作。比如：

```python
def func(url):
    return { 'bucket': 'scrapy', 'key': 'key_name/%s' % hashlib.md5(url).hexdigest() }
    
item['qiniu_key_generator'] = func
```

在这样的情况下，item的`file_urls`字段所指定的资源，会被七牛服务器fetch到`scrapy`这个bucket中，并且key的命名形式为：`key_name/{md5_hash}`。
