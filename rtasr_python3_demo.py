# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
import io
import subprocess
from socket import *
import json, time, threading
from websocket import create_connection
import websocket
from urllib.parse import quote
import logging

from util.logger import setup_logger
from util.utils import generate_current_time


# reload(sys)
# sys.setdefaultencoding("utf8")
class Client():
    def __init__(self):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')

        apiKey = api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        self.end_tag = "{\"end\": true}"
        current_time = generate_current_time()
        self.asr_logger = setup_logger("xunfei_asr_logger", id=current_time)

        self.ws = create_connection(base_url + "?appid=" + app_id + "&ts=" + ts + "&signa=" + quote(signa)+"&lang=cn_cantonese"+"&roleType=2")
        #self.ws = create_connection("ws://rtasr.xfyun.cn/v1/ws?appid=595f23df&ts=1512041814&signa=IrrzsJeOFk1NGfJHW6SkHUoN9CU=&pd=edu")
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()

    def resample_audio(self,input_file, sample_rate=16000):
        """
        使用 FFmpeg 对 WAV 格式的音频文件进行重采样。

        参数:
            input_file (str): 输入音频文件路径
            output_file (str): 输出音频文件路径
            sample_rate (int): 目标采样率，默认为 16000 Hz
        """
        output_file = "/Users/microware/Downloads/output_resampled.wav"  # 输出文件路径

        # 构造 FFmpeg 命令
        command = [
            "ffmpeg",  # FFmpeg 命令
            "-i", input_file,  # 输入文件
            "-ar", str(sample_rate),  # 设置目标采样率
            "-ac", "1",  # 设置声道数量为单声道（1）
            # "-acodec", "pcm_s16le",  # 设置音频编码格式为 PCM 16-bit little-endian
            "-f", "s16le",  # 指定输出格式为 WAV
            "-"  # 输出到标准输出
        ]

        # 使用 subprocess.Popen 执行命令
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024)
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                yield chunk
            if process.returncode == 0:
                print(f"音频重采样完成")
            else:
                # 将错误信息从 bytes 解码为字符串
                error_message = process.stderr.decode('utf-8') if isinstance(process.stderr, bytes) else process.stderr
                print(f"音频重采样失败。错误信息：{error_message}")
        except Exception as e:
            print(f"执行 FFmpeg 命令时出错：{e}")
        finally:
            # 确保子进程被正确关闭
            process.stdout.close()
            process.stderr.close()
            process.wait()
    def send(self, file_path):
        # try:
        #     # while True:
        #         for chunk in self.resample_audio(input_file=file_path):
        #             if not chunk:
        #                 break
        #             self.ws.send(chunk)
        #             time.sleep(0.04)
        #         self.ws.send(bytes(self.end_tag.encode('utf-8')))
        #         print("send end tag success")
        # except Exception as ex:
        #     print(f"audio chunk error:{str(ex)}")

        file_object = open(file_path, 'rb')
        try:
            index = 1
            while True:
                chunk = file_object.read(1280)
                if not chunk:
                    break
                self.ws.send(chunk)

                index += 1
                time.sleep(0.04)
        finally:
            file_object.close()

        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("send end tag success")

    def recv(self):

        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("receive result end")
                    break
                result_dict = json.loads(result)
                # 解析结果
                if result_dict["action"] == "started":
                    print("handshake success, result: " + result)

                if result_dict["action"] == "result":
                    result_1 = result_dict
                    # result_2 = json.loads(result_1["cn"])
                    # result_3 = json.loads(result_2["st"])
                    # result_4 = json.loads(result_3["rt"])
                    #print("rtasr result: " + result_1["data"])
                    #if result_1["cn"]["type"] == "0":
                    tem_str_dict=json.loads(result_1["data"])
                    tem_rs=tem_str_dict["cn"]["st"]["rt"][0]["ws"]
                    if tem_str_dict["cn"]["st"]["type"] == "0":
                        ws_text=""
                        start_time=tem_str_dict["cn"]["st"]["bg"]
                        end_time=tem_str_dict["cn"]["st"]["ed"]
                        speak_num =""
                        output = io.StringIO()
                        for tt in tem_rs:
                          if tt["cw"][0]["wp"]=="p":
                             continue
                          ws_text=ws_text+tt["cw"][0]["w"]
                          print(f"chunk:{str(ws_text)}")
                          speak_num=ws_text.join(tt["cw"][0]["rl"])
                          output.write(tt["cw"][0]["w"])
                          #output.write(" ")
                        speech_word = output.getvalue()
                        self.asr_logger.info(f"{True}##{speak_num}##{start_time}##{end_time}##{speech_word}")
                        print("ws_text:"+speech_word+",start_time:"+start_time+",end_time:"+end_time+",speak_num:"+speak_num)
                        # 清空内容
                        output.seek(0)  # 将指针移动到文件开头
                        output.truncate()  # 从当前位置截断内容，清空整个内容

                if result_dict["action"] == "error":
                    print("rtasr error: " + result)
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            print("receive result end")

    def close(self):
        self.ws.close()
        print("connection closed")


if __name__ == '__main__':
    try:
        logging.basicConfig()

        app_id = "59c453fd"
        api_key = "371e3ccf420ec5ba6a086858ec071b5e"
        #api_key ="bcaab8a153c1a62c90ef2f416b26277d"
        #file_path = r"./test_1.pcm"
        #file_path = "/Users/microware/Downloads/中多人35m.MP3"
        #file_path = "/Users/microware/Desktop/temp/HR_commision_4min.wav"
        #file_path = "/Users/microware/Desktop/temp/3-fW99oaYMY.m4a" #粤英 测试音频1
        #file_path ="/Users/microware/Desktop/temp/IFxnw0NBez0.m4a" #粤英 测试音频2
        file_path ="/Users/microware/Desktop/temp/粤语demo.wav"
        #file_path = "/Users/microware/Desktop/temp/iphone1.wav"

        client = Client()
        client.send(file_path)
    except Exception as ex:
        print(f"error:{str(ex)}")
