import websocket
import base64
import hmac
import json
import time
import os
import sys
import logging
import typing
import argparse
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel('INFO')
logger.addHandler(logging.NullHandler())


class TTS:
    default_business_options = {'aue': 'lame', 'sfl': 1, 'vcn': 'xiaoyan', 'tte': 'utf8'}

    @classmethod # py3.9才支持与@property()一起使用
    def busopt_man(cls):
        '''使用男声的便捷方法'''
        return dict(cls.default_business_options, **{'vcn': 'aisjiuxu'})

    def __init__(self, appid: str, apisecret: typing.AnyStr, apikey: typing.AnyStr):
        assert 6 < len(appid) < 10, 'Wrong appid'  # 我的是8
        assert len(apisecret) == 32, 'Wrong apisecret'
        assert len(apikey) == 32, 'Wrong apikey'

        self.appid = appid
        self.apisecret = apisecret if isinstance(apisecret, bytes) else apisecret.encode()
        self.apikey = apikey if isinstance(apikey, bytes) else apikey.encode()

    def get_request_body(self, text: bytes, business_options: typing.Optional[dict] = None):
        '''用于ws.send()的内容'''
        body = {
            'common': {'app_id': self.appid},
            'business':  business_options or self.default_business_options,
            'data': {'status': 2, 'text': base64.b64encode(text).decode()},
        }
        logger.debug('body: %s', body)

        return json.dumps(body)

    def get_api_endpoint(self):
        '''根据 apikey apisecret 当前时间 生成URL，无需appid'''

        # 生成RFC1123格式的时间戳
        date = format_date_time(time.time())

        # 签名的原始字段
        sig_origin = b'host: tts-api.xfyun.cn\ndate: %s\nGET /v2/tts HTTP/1.1' % date.encode()

        # hmac-sha256加密
        sig_sha = hmac.digest(self.apisecret, sig_origin, 'sha256')
        sig_sha = base64.b64encode(sig_sha)

        auth_origin = b'api_key="%s", algorithm="hmac-sha256", headers="host date request-line", signature="%s"' % (self.apikey, sig_sha)
        auth = base64.b64encode(auth_origin).decode()

        # 将请求的鉴权参数组合为字典
        v = {
            'host': 'tts-api.xfyun.cn',
            'date': date,
            'authorization': auth,
        }
        logger.debug('auth: %s', v)

        # 拼接鉴权参数
        return 'wss://tts-api.xfyun.cn/v2/tts?' + urlencode(v)

    def receive(self, ws: websocket.WebSocket):
        '''内容分多次返回，服务端保证每次都是完整的json'''
        while True:
            message = ws.recv()
            logger.info('received.')

            message = json.loads(message)
            logger.debug('message: %s', message)

            if message['code']:  # !=0
                logger.error('sid %s call error %s code is %s' %
                             (message['sid'], message['message'], message['code']))
                return

            yield base64.b64decode(message['data']['audio'])

            if message['data']['status'] == 2:
                # 表示结束，注意当前message仍存在有效数据，已在上一行处理，但就不方便单独用一个函数处理message了
                return

    def send_once(self, ws: websocket.WebSocket, text: bytes, busopt: typing.Optional[dict] = None):
        '''服务端要求text在base64编码前的长度小于8000字节'''
        assert len(text) < 8000, 'text too long'

        body = self.get_request_body(text, busopt)

        logger.info('sending.')
        ws.send(body)

        yield from self.receive(ws)

    def get_stream(self, text: typing.AnyStr, busopt: typing.Optional[dict] = None):
        '''流式API。如果text长度超过2500，分块请求；但bytes无法分块，因为u8一个中字3字节，英文1字节，无法确定在哪分开'''
        wsurl = self.get_api_endpoint()
        ws = websocket.create_connection(wsurl, skip_utf8_validation=True)
        logger.info('connected.')

        if isinstance(text, bytes):
            yield from self.send_once(ws, text, busopt)
        else:
            for chunk in (text[i:i+2500] for i in range(0, len(text), 2500)):
                yield from self.send_once(ws, chunk.encode(), busopt)

        logger.info('end.')
        ws.close()

    def get(self, text: str):
        '''简单API'''
        return b''.join(self.get_stream(text))


def _main():
    '''命令行接口'''
    parser = argparse.ArgumentParser(description='xfyun online TTS')
    parser.add_argument('file', help='use - for stdin')
    parser.add_argument('-d', action='store_true', help='enable massive debug log')
    args = parser.parse_args()

    if args.d:
        websocket.enableTrace(True)
        logging.basicConfig(level='DEBUG', format='%(asctime)s %(levelname)s:%(message)s')
    else:
        logging.basicConfig(level='INFO', format='%(asctime)s %(levelname)s:%(message)s')

    # 处理环境变量提供的选项
    (appid, apisecret, apikey, busopt) = (os.getenv('XFYUN_APPID'), os.getenv('XFYUN_APISECRET'), os.getenv('XFYUN_APIKEY'), os.getenv('XFYUN_BUSOPT'))
    assert appid and apisecret and apikey, 'missing XFYUN_XXX environment variables'
    if busopt:
        busopt = TTS.busopt_man() if busopt == 'MAN' else json.loads(busopt)
    assert busopt is None or isinstance(busopt, dict)

    tts = TTS(appid, apisecret, apikey)

    # 支持从stdin或文件中读入
    if args.file == '-':
        text = sys.stdin.buffer.read()
        if not text:
            logger.warning('no data from stdin')
            return
        for data in tts.get_stream(text, busopt):
            sys.stdout.buffer.write(data)
    else:
        if not os.path.isfile(args.file):
            logger.warning(args.file + ' is not file')
            return

        with open(args.file, encoding='utf8') as f:
            text = f.read()
        if not text.strip():
            logger.warning('no data from file')
            return

        with open(Path(args.file).with_suffix('.mp3'), 'wb') as f:
            for data in tts.get_stream(text, busopt):
                f.write(data)


if __name__ == '__main__':
    _main()
