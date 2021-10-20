# [讯飞语音合成(TTS)流式版WebAPI](https://www.xfyun.cn/services/online_tts)

本项目参考官方Demo实现了TTS流式版(WebSocket)WebAPI客户端，既可以作为库使用，又提供命令行接口。

## 平台

实名认证后“服务量”有一定的免费额度：

* https://www.xfyun.cn/services/online_tts?target=price
* https://www.xfyun.cn/customerLevel

使用前考虑阅读隐私协议和服务协议：https://www.xfyun.cn/doc/policy/privacy.html

Secrets和可用的发音人在控制台中查看，免费的发音人只有基础的五个：https://console.xfyun.cn/services/tts

## 安装和卸载

```cmd
pip install git+https://github.com/imba-tjd/xfyun-tts-v2
pip uninstall xfyun-tts
```

## 使用

官方文档：https://www.xfyun.cn/doc/tts/online_tts/API.html

本项目没有做任何异常捕获，业务错误请参见文档的 #错误码。

格式默认为mp3，发音人为小燕，语速 音量 音高均为默认值；如果想更改，先阅读文档的 #业务参数说明-business。

### 命令行

必须先设置XFYUN_APPID XFYUN_APISECRET XFYUN_APIKEY三个环境变量，bash用export，pwsh用$env。

若想修改business_options，设置XFYUN_BUSOPT环境变量，确保能被`json.loads()`解析成dict，或设为`MAN`表示预定义的便捷方式使用男声。

确保你明白什么是CWD。

```bash
xfyuntts -h  # 命令行帮助
xfyuntts demo.txt  # 生成demo.mp3
cat demo.txt | xfyuntts - > demo.mp3  # 另一种方法，横杠不可省；字面量用echo xxx传入；pwsh不支持
```

### 库

给xfyun_tts.logger添加handler能获取日志，默认不会主动有任何输出。

```py
from xfyun_tts import TTS

tts = TTS(appid, apisecret, apikey) # 改成使用者的

with open('./demo.mp3', 'wb') as f: # 必须以b即二进制模式打开
    for data in tts.get_stream('这是一个语音合成示例'): # 可选传入busopt，提供tts.busopt_man便捷方式使用男声
        f.write(data)
```

## Won't fix

* 命令行以文件为参数时保存的后缀只能是mp3。检测业务配置好像也不算特别麻烦，但我不用其他格式
