import logging
import time

from config import setup_custom_logger

bailian_api_key = 'sk-ca3dbfd800ff441cb5be165d82c3390d'
# For prerequisites running the following sample, visit https://help.aliyun.com/zh/model-studio/getting-started/first-api-call-to-qwen
import os
import signal  # for keyboard events handling (press "Ctrl+C" to terminate recording and translation)
import sys

import dashscope
import pyaudio
from dashscope.audio.asr import *

mic = None
stream = None

# Set recording parameters
sample_rate = 16000  # sampling rate (Hz)
channels = 1  # mono channel
dtype = 'int16'  # data type
format_pcm = 'pcm'  # the format of the audio data
block_size = 3200  # number of frames per buffer


def init_dashscope_api_key():
    """
        Set your DashScope API-key. More information:
        https://github.com/aliyun/alibabacloud-bailian-speech-demo/blob/master/PREREQUISITES.md
    """

    if 'DASHSCOPE_API_KEY' in os.environ:
        dashscope.api_key = os.environ[
            'DASHSCOPE_API_KEY']  # load API-key from environment variable DASHSCOPE_API_KEY
    else:
        dashscope.api_key = bailian_api_key  # set API-key manually


# Real-time speech recognition callback
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print('RecognitionCallback open.')
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True)

    def on_close(self) -> None:
        global mic
        global stream
        print('RecognitionCallback close.')
        stream.stop_stream()
        stream.close()
        mic.terminate()
        stream = None
        mic = None

    def on_complete(self) -> None:
        print('RecognitionCallback completed.')  # translation completed

    def on_error(self, message) -> None:
        print('RecognitionCallback task_id: ', message.request_id)
        print('RecognitionCallback error: ', message.message)
        # Stop and close the audio stream if it is running
        if 'stream' in globals() and stream.active:
            stream.stop()
            stream.close()
        # Forcefully exit the program
        sys.exit(1)

    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        if 'text' in sentence:
            sentence_end = result.is_sentence_end(sentence)
            # 一句完整的话sentence里包含end_time
            if sentence_end:
                sentence_info = f"{sentence_end}##UNKNOWSPK##{sentence['begin_time']}##{sentence['end_time']}##{sentence['text']}"
            else:
                # 没说完的话end_time 在words中
                if len(sentence["words"]) > 1:
                    sentence_end_time = sentence["words"][-2]["end_time"]
                elif len(sentence["words"]) == 1:
                    sentence_end_time = sentence["words"][-1]["end_time"]
                else:
                    sentence_end_time = sentence["begin_time"]
                sentence_info = f"{sentence_end}##UNKNOWSPK##{sentence['begin_time']}##{sentence_end_time}##{sentence['text']}"

            # print("words:====", sentence["words"])
            print('RecognitionCallback text: ', sentence_info)
            # if RecognitionResult.is_sentence_end(sentence):
            #     print(
            #         'RecognitionCallback sentence end, request_id:%s, usage:%s'
            #         % (result.get_request_id(), result.get_usage(sentence)))


def microphone_demo():
    def signal_handler(sig, frame):
        print('Ctrl+C pressed, stop translation ...')
        # Stop translation
        recognition.stop()
        print('Translation stopped.')
        print(
            '[Metric] requestId: {}, first package delay ms: {}, last package delay ms: {}'
            .format(
                recognition.get_last_request_id(),
                recognition.get_first_package_delay(),
                recognition.get_last_package_delay(),
            ))
        # Forcefully exit the program
        sys.exit(0)

    """捕获当前设备麦克风进行asr"""
    # Create the translation callback
    callback = Callback()

    # Call recognition service by async mode, you can customize the recognition parameters, like model, format,
    # sample_rate For more information, please refer to https://help.aliyun.com/document_detail/2712536.html
    recognition = Recognition(
        model='paraformer-realtime-v2',
        # 'paraformer-realtime-v1'、'paraformer-realtime-8k-v1'
        format=format_pcm,
        # 'pcm'、'wav'、'opus'、'speex'、'aac'、'amr', you can check the supported formats in the document
        sample_rate=sample_rate,
        # support 8000, 16000
        semantic_punctuation_enabled=False,  # 延迟敏感的场景建议设置为False
        language_hints=["en"],
        callback=callback)

    # Start translation
    recognition.start()

    signal.signal(signal.SIGINT, signal_handler)
    print("Press 'Ctrl+C' to stop recording and translation...")
    # Create a keyboard listener until "Ctrl+C" is pressed

    while True:
        if stream:
            data = stream.read(3200, exception_on_overflow=False)
            recognition.send_audio_frame(data)
        else:
            break

    recognition.stop()


def wav_demo():
    from datetime import datetime

    def get_timestamp():
        now = datetime.now()
        formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
        return formatted_timestamp

    class Callback(RecognitionCallback):
        def on_complete(self) -> None:
            print(get_timestamp() + ' Recognition completed')  # recognition complete

        def on_error(self, result: RecognitionResult) -> None:
            print('Recognition task_id: ', result.request_id)
            print('Recognition error: ', result.message)
            exit(0)

        def on_event(self, result: RecognitionResult) -> None:
            sentence = result.get_sentence()
            if 'text' in sentence:
                sentence_end = result.is_sentence_end(sentence)
                # 一句完整的话sentence里包含end_time
                if sentence_end:
                    sentence_info = f"{sentence_end}##UNKNOWSPK##{sentence['begin_time']}##{sentence['end_time']}##{sentence['text']}"
                    logging.info(f'{sentence_info}')
                else:
                    # 没说完的话end_time 在words中
                    if len(sentence["words"]) > 1:
                        sentence_end_time = sentence["words"][-1]["end_time"]
                    else:
                        sentence_end_time = sentence["begin_time"]
                    sentence_info = f"{sentence_end}##UNKNOWSPK##{sentence['begin_time']}##{sentence_end_time}##{sentence['text']}"
                # print(get_timestamp() + ' RecognitionCallback text: ', sentence['text'])
                # print("===words:", sentence['words'])
                # if RecognitionResult.is_sentence_end(sentence):
                #     print(get_timestamp() +
                #           'RecognitionCallback sentence end, request_id:%s, usage:%s'
                #           % (result.get_request_id(), result.get_usage(sentence)))

    callback = Callback()

    recognition = Recognition(model='paraformer-realtime-v2',
                              format='wav',
                              sample_rate=16000,
                              # “language_hints”只支持paraformer-realtime-v2模型
                              language_hints=['zh', 'en'],
                              callback=callback)

    recognition.start()

    try:
        audio_data: bytes = None
        file_path: str = "HR_commision_4min.wav"
        f = open(file_path, 'rb')
        if os.path.getsize(file_path):
            while True:
                audio_data = f.read(3200)
                if not audio_data:
                    break
                else:
                    recognition.send_audio_frame(audio_data)
                time.sleep(0.1)
        else:
            raise Exception(
                'The supplied file was empty (zero bytes long)')
        f.close()
    except Exception as e:
        raise e

    recognition.stop()

    print(
        '[Metric] requestId: {}, first package delay ms: {}, last package delay ms: {}'
        .format(
            recognition.get_last_request_id(),
            recognition.get_first_package_delay(),
            recognition.get_last_package_delay(),
        ))


# main function
if __name__ == '__main__':
    setup_custom_logger()
    init_dashscope_api_key()
    print('Initializing ...')
    # 麦克风asr
    # microphone_demo()

    # wav demo
    wav_demo()
