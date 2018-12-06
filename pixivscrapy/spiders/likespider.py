# coding: utf-8

import re
import os
import scrapy
import urllib2
from scrapy.http import Request
from pixivscrapy.config import config
from pixivscrapy.namemanage.namemanage import name_manage

try:
    import urlparse
except:
    import urllib.parse as urlpase


class Likespider(scrapy.Spider):

    name = 'Pixiv_spider'
    # allowed_domains = ['https://www.pixiv.net/']
    # start_urls = ["https://www.pixiv.net/"]
    username = config.Account_config.get("User_1").get("username")
    passwd = config.Account_config.get("User_1").get("passwd")
    save_path = config.Account_config.get("User_1").get("save_path")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        "Connection": "keep-alive",
        "Content-Type": " application/x-www-form-urlencoded; charset=UTF-8",
    }

    def start_requests(self):
        return [Request(url="https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index",
                        callback=self.post_login, dont_filter=True, meta={'cookiejar': 1})]

    def post_login(self, response):
        post_key_raw = response.xpath("//*[@id='old-login']/form/input[1]/@value").extract()
        if not post_key_raw:
            return
        post_key = post_key_raw[0]
        return [scrapy.FormRequest.from_response(response, meta={'cookiejar': response.meta['cookiejar']},
                                                 headers=self.headers,
                                                 formdata={'pixiv_id': self.username, 'password': self.passwd,
                                                           'captcha': None, 'g_recaptcha_response': None,
                                                           'post_key': post_key, 'source': 'pc',
                                                           'ref': 'wwwtop_accounts_index',
                                                           'return_to': 'https://www.pixiv.net'},
                                                 callback=self.after_login, dont_filter=True)]

    def after_login(self, response):
        # many pages???
        yield scrapy.Request(url="https://www.pixiv.net/bookmark.php?type=user", callback=self.parse, dont_filter=True,
                              meta={'cookiejar': response.meta['cookiejar']})

    def parse(self, response):
        like_list = response.xpath("//*[@id='search-result']/div/ul/li/input/@value").extract()
        like_name = response.xpath("//*[@id='search-result']/div/ul/li/a/@data-user_name").extract()
        if not like_list:
            return
        for like_i in range(len(like_list)):
            id_url = 'https://www.pixiv.net/ajax/user/{0}/profile/all'.format(like_list[like_i])
            path_1 = self.save_path + "\\" + name_manage(like_name[like_i])
            if not os.path.exists(path_1):
                os.makedirs(path_1)
            yield scrapy.Request(url=id_url, callback=self.parse_item, dont_filter=True, priority=3,
                                 meta={'cookiejar': response.meta['cookiejar'], 'file_path': path_1})

    def parse_item(self, response):
        # print response.body
        re_id = re.compile('"(\d*?)":null')
        img_id = re_id.findall(response.text)
        if not img_id:
            return
        for picture in img_id:
            big_picture_url = "https://www.pixiv.net/ajax/illust/{0}".format(picture)
            yield scrapy.Request(url=big_picture_url, callback=self.parse_item_item, dont_filter=True, priority=2,
                           meta={'cookiejar': response.meta['cookiejar'], 'file_path': response.meta['file_path'], 'picture_id': picture})

    def parse_item_item(self, response):
        re_name = re.compile('"illustTitle":"(.*?)"')
        re_url = re.compile('"regular":"(.*?)"')
        img_name = name_manage(re_name.findall(response.text)[0].decode('gb2312'))
        img_url = re_url.findall(response.text)[0].replace('\\','')
        picture_id = response.meta['picture_id']
        if img_name and img_url:
            url_re = re.compile('https://i.pximg.net/(.*)')
            picture_path = url_re.findall(img_url)
            if not picture_path:
                return
            postfix = img_url.split('.')[-1]
            file_path = response.meta['file_path'] + '\\' + img_name + '_' + picture_id + '.' + postfix
            header = {'authority': 'i.pximg.net', 'method': 'GET', 'path': picture_path[0],
                      'scheme': 'https', 'accept': 'image/webp,image/apng,image/*,*/*;q=0.8', 'accept-encoding': 'gzip, deflate, br',
                      'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6','referer': response.url,
                      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
            request = urllib2.Request(img_url, None, header)
            response = urllib2.urlopen(request)
            with open(file_path, "wb") as f:
                f.write(response.read())
        else:
            return
            '''
            redirect_url = response.url.replace("medium", "manga")
            file_path = response.meta['file_path'] + '\\' + response.meta['file_name']
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            yield scrapy.Request(url=redirect_url, callback=self.parse_item_item_item, dont_filter=True, priority=1,
                                 meta={'cookiejar': response.meta['cookiejar'], 'file_path': file_path,
                                       'file_name': response.meta['file_name'], 'picture_id': picture_id})
                                       '''

    def parse_item_item_item(self, response):
        big_picture_src = response.xpath("//*[@id='main']/section/div/img/@data-src").extract()
        picture_id = response.meta['picture_id']
        url_re = re.compile('https://i.pximg.net/img-master/(.*)_master1200.jpg')
        file_path = response.meta['file_path']
        file_name = response.meta['file_name']
        for counter in range(0, len(big_picture_src)):
            picture = big_picture_src[counter]
            picture_path = url_re.findall(picture)
            if picture_path:
                post_fix = picture.split('.')[-1]
                picture_path_c = "img-original/" + picture_path[0] + '.' + post_fix
                picture_path[0] = "https://i.pximg.net/img-original/" + picture_path[0] + '.' + post_fix

                file_path_at = file_path + '\\' + file_name + '_' + picture_id + '_p' + str(counter) + '.' + post_fix
                header = {'authority': 'i.pximg.net', 'method': 'GET', 'path': picture_path_c,
                          'scheme': 'https', 'accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                          'accept-encoding': 'gzip, deflate, br',
                          'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6', 'referer': response.url,
                          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
                request = urllib2.Request(picture_path[0], None, header)
                response = urllib2.urlopen(request)
                with open(file_path_at, "wb") as f:
                    f.write(response.read())


