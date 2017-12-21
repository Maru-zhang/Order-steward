#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import random
import json
import sys
import smtplib
import logging
from logging import Logger, NOTSET
from email.mime.text import MIMEText
from email.header import Header
from smtplib import SMTP_SSL

import requests

from config import config

CJD_HOST = 'https://cjdwos.hz.taeapp.com'
NULL_Flag = 'none'

config_path = os.getenv("HOME") + "/.config/SCCOrderStrategy.json"

logger = logging.Logger(name='order-logger', level=NOTSET)

class Steward(object):

    def __init__(self):
        self.token = 'a992317e7290c8d15b132013776bc03f'
        self.email = ''
        self.source = 'dingding'
        self.version = '2.4.4'
        self.smtp_server = 'smtp.163.com'
        self.smtp_client = None
        self._name = '订餐小助手'
        self._master_email = None
        self._master_email_pwd = None
        self.black_list = None
        try:
            with open(os.getcwd() + '/security_account') as file:
                self._master_email = file.read()
            with open(os.getcwd() + '/security_password') as file:
                self._master_email_pwd = file.read()
            print(self._master_email)
            print(self._master_email_pwd)
        except Exception as e:
            print(e)

    def run(self):
        try:
            file = open(config_path, 'w+')
            data = file.read()
            configs = data.values()
            if not data:
                data = config
                file.write(json.dumps(data))             
        except Exception as e:
            configs = config.values()
        try:
            for body in configs:
                self.token = body["token"]
                self.black_list = body['black'].split(',')
                self.email = body['email']
                self.excutePeerJob()
        except KeyError:
            print('Nothing to excute ...')
    
    def run_test(self):
        self.excutePeerJob()
        
    def excutePeerJob(self):
        shop_list_json = self._fetch_today_shop()
        try:
            shop_list = shop_list_json['data']['memberList']
            filter_shop_list = list(filter(lambda x: x['memberName'] not in self.black_list, shop_list))
            print(filter_shop_list)
            shop = random.choice(filter_shop_list)
            shop_id = shop['memberId']
            print('选择的店铺为' + str(shop_id))
            logger.info(shop)
            shop_menu_json = self._fetch_shop_menu(shop_id)
            shop_name = shop_menu_json['data']['list'][0]['mname']
            shop_menu = shop_menu_json['data']['list'][0]['list']
            meal_json = random.choice(shop_menu)
            meal_name = meal_json['title']
            meal_price = meal_json['price']
            meal_id = meal_json['id']
            print('选择的菜品id为' + meal_id)
            self._is_place_order(meal_id)
            address_id = self._confirm_order(meal_id)['data']['address'][0]['id']
            print('地址id为' + address_id)
            self._save_order(meal_id, address_id)
            print('订单完成')
            message = '''今天为您预定的是 %s 的 %s
该菜品的价格为: %s人民币
享受今天的工作餐吧~
            ''' % (shop_name, meal_name, meal_price)
            self.send_email(subject='今天的工作餐', to_account=self.email, content=message)
        except Exception as e:
            logger.error(e)

    def send_email(self, to_account, subject, content):
        email_client = smtplib.SMTP(self.smtp_server)
        email_client.login(self._master_email, self._master_email_pwd)
        # create msg
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')  # subject
        msg['From'] = self._name
        msg['To'] = to_account
        email_client.sendmail(self._master_email, to_account, msg.as_string())
        email_client.quit()

    def _fetch_today_shop(self):
        req = requests.post(self._cjd_url_today_shop, data=self._cjd_post_params, verify=False)
        return req.json()

    # 我也不知道这个接口干嘛用的
    def _is_place_order(self, meal_id):
        data = self._cjd_post_params
        data['items'] = meal_id + ':1;'
        r = requests.get(self._cjd_url_place_order, params=data, verify=False)
        print(r.json())

    # 确认订单, 返回地址ID
    def _confirm_order(self, meal_id):
        data = self._cjd_post_params
        data['items'] = meal_id + ':1;'
        r = requests.post(self._cjd_url_confirm_order, data=data, verify=False)
        return r.json()

    # 保存订单
    def _save_order(self, meal_id, address_id):
        data = self._cjd_post_params
        data['items'] = meal_id + ':1;'
        data['addrId'] = address_id
        r = requests.post(self._cjd_url_save_order, data=data, verify=False)
        print(r.json())

    # 获取某个店铺的菜单
    def _fetch_shop_menu(self, shop_id):
        r = requests.get(self._cjd_url_shop_menu, params=self._cjd_get_menu_params(shop_id=shop_id), verify=False)
        return r.json()

    def _cjd_get_menu_params(self, shop_id):
        today = time.strftime("%Y-%m-%d", time.localtime())
        return {"token": self.token, "source": self.source, "version": self.version, "date": today, "type": "3", "mid": shop_id, "sort": "asc HTTP/1.1"}

    @property
    def _cjd_post_params(self):
        today = time.strftime("%Y-%m-%d", time.localtime())
        return {"token": self.token, "source": self.source, "version": self.version, "date": today, "mealType": "3"}

    @property
    def _cjd_url_confirm_order(self):
        return self._order_url('/order/confirmOrder')

    @property
    def _cjd_url_save_order(self):
        return self._order_url('/order/saveOrder')

    @property
    def _cjd_url_place_order(self):
        return self._order_url('/order/isPlaceOrder')

    @property
    def _cjd_url_today_shop(self):
        return self._order_url('/order/currentDateMember')

    @property
    def _cjd_url_shop_menu(self):
        return self._order_url('/order/getMenu')

    def _order_url(self, path):
        return CJD_HOST + path

if __name__ == '__main__':
    
    try:
        args = sys.argv
        user_id = args[1]
        if (not user_id == 'none') and user_id:
            file = open(config_path, 'w+')
            origin_data = file.read()
            if not origin_data:
                origin_data = config
            print(origin_data)
            try:
                origin_user = origin_data[user_id]
            except KeyError:
                origin_user = {}
            if not origin_user:
                # config data
                origin_user = {}
                token = args[2]
                black = args[3]
                email = args[4]
                if token != NULL_Flag:
                    origin_user['token'] = token
                if black != NULL_Flag:
                    origin_user['black'] = black
                if email != NULL_Flag:
                    origin_user['email'] = email
            origin_data[user_id] = origin_user
            file.write(json.dumps(origin_data))
    except Exception as e:
        print(e)
    finally:
        s = Steward()
        s.run()