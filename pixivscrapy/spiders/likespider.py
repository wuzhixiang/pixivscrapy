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
    allowed_domains = ['https://www.pixiv.net/']
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
        if not like_list:
            return
        for like_id in like_list:
            for page in range(1, 20):
                id_url = 'https://www.pixiv.net/member_illust.php?id={0}&type=all&p={1}'.format(like_id, page)
                yield scrapy.Request(url=id_url, callback=self.parse_item, dont_filter=True, priority=3,
                                     meta={'cookiejar': response.meta['cookiejar']})
        

    def parse_item(self, response):
        like_user_name = response.xpath("//*[@id='wrapper']/div[1]/div[2]/div/div[1]/a/h1/text()").extract()[0]
        path_1 = self.save_path + "\\" + name_manage(like_user_name)
        if not os.path.exists(path_1):
            os.makedirs(path_1)
        re_id = re.compile("id=(.*)")
        img_src_set = response.xpath("//*[@id='wrapper']/div[1]/div[1]/div/div[4]/ul/li/a[1]/@href").extract()
        img_name_set = response.xpath("//*[@id='wrapper']/div[1]/div[1]/div/div[4]/ul/li/a[2]/h1/@title").extract()
        #img_src_set = list(set(img_src))
        #img_src_set.sort(key=img_src.index)
        #img_name_set = list(set(img_name))
        #img_name_set.sort(key=img_name.index)
        like_picture = []
        for counter in range(0, len(img_src_set)):
            if re_id.findall(img_src_set[counter]):
                like_picture_info = {'src': re_id.findall(img_src_set[counter])[0], 'name': img_name_set[counter]}
                like_picture.append(like_picture_info)
        for picture in like_picture:
            file_name = name_manage(picture['name']) + ''
            big_picture_url = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id={0}".format(picture['src'])
            yield scrapy.Request(url=big_picture_url, callback=self.parse_item_item, dont_filter=True, priority=2,
                           meta={'cookiejar': response.meta['cookiejar'], 'file_path': path_1, 'file_name': file_name,
                                 'picture_id': picture['src']})

    def parse_item_item(self, response):
        big_picture_src = response.xpath("//*[@id='wrapper']/div[2]/div/img/@data-src").extract()

        picture_id = response.meta['picture_id']
        if big_picture_src:
            url_re = re.compile('https://i.pximg.net/(.*)')
            picture_path = url_re.findall(big_picture_src[0])
            if not picture_path:
                return
            postfix = big_picture_src[0].split('.')[-1]
            file_path = response.meta['file_path'] + '\\' + response.meta['file_name'] + '_' + picture_id + '.' + postfix
            header = {'authority': 'i.pximg.net', 'method': 'GET', 'path': picture_path[0],
                      'scheme': 'https', 'accept': 'image/webp,image/apng,image/*,*/*;q=0.8', 'accept-encoding': 'gzip, deflate, br',
                      'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6','referer': response.url,
                      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
            request = urllib2.Request(big_picture_src[0], None, header)
            response = urllib2.urlopen(request)
            with open(file_path, "wb") as f:
                f.write(response.read())
        else:
            redirect_url = response.url.replace("medium", "manga")
            file_path = response.meta['file_path'] + '\\' + response.meta['file_name']
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            yield scrapy.Request(url=redirect_url, callback=self.parse_item_item_item, dont_filter=True, priority=1,
                                 meta={'cookiejar': response.meta['cookiejar'], 'file_path': file_path,
                                       'file_name': response.meta['file_name'], 'picture_id': picture_id})

    def parse_item_item_item(self, response):
        big_picture_src = response.xpath("//*[@id='main']/section/div/img/@data-src").extract()
        picture_id = response.meta['picture_id']
        url_re = re.compile('https://i.pximg.net/(.*)')
        file_path = response.meta['file_path']
        file_name = response.meta['file_name']
        for counter in range(0, len(big_picture_src)):
            picture = big_picture_src[counter]
            picture_path = url_re.findall(picture)
            if picture_path:
                post_fix = picture.split('.')[-1]
                file_path_at = file_path + '\\' + file_name + '_' + picture_id + '_p' + str(counter) + '.' + post_fix
                header = {'authority': 'i.pximg.net', 'method': 'GET', 'path': picture_path[0],
                          'scheme': 'https', 'accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                          'accept-encoding': 'gzip, deflate, br',
                          'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6', 'referer': response.url,
                          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
                request = urllib2.Request(picture, None, header)
                response = urllib2.urlopen(request)
                with open(file_path_at, "wb") as f:
                    f.write(response.read())


