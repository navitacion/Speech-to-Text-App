import time, datetime, wave, base64, os, uuid
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy.io import wavfile
import youtube_dl
from pydub import AudioSegment

import azure.cognitiveservices.speech as speechsdk


class AudioReader:
    def __init__(self, origin='file', length=180, blob_client=None):
        self.today = datetime.now(tz=timezone(timedelta(hours=+9), 'JST'))
        self.today = self.today.strftime('%Y%m%d-%H%M%S')
        self.audio_file_path = f'./tmp/audio_{self.today}_{uuid.uuid4()}.wav'

        self.origin = origin
        self.length = length
        self.blob_client = blob_client


    def _preprocess(self, audio):
        """
        AudioSegment形式データの前処理
        ---------------------------
        Parameters

        audio: pydub.AudioSegment
            音声データ

        ---------------------------
        Returns

        audio: pydub.AudioSegment
            前処理後の音声データ
        """
        audio = audio.set_channels(1)

        return audio


    def read_write_tmp_file(self, inp, save_to_blob=False):
        """
        BytesIO形式やYouTube URLを元に音声ファイルを読み込む
        前処理をかけた後、一次ファイルとしてWAVファイルで保存する
        pathはself.audio_file_path
        """
        if self.origin == 'file':
            audio = self.from_byte(inp)
        elif self.origin == 'youtube':
            audio = self.from_YouTube(inp)

        else:
            raise NotImplementedError

        # 前処理
        audio = self._preprocess(audio)
        # tmpとしてWAVで保存
        audio.export(self.audio_file_path, format='wav')

        # 元の音声ファイルをBlobに保存
        if save_to_blob:
            self.blob_client.create_blob_from_path(
                'speechaudiofiles',
                self.audio_file_path.split('/')[-1],
                self.audio_file_path)


    def from_byte(self, byte_file):
        """
        BytesIO形式のwavファイルを読み込む
        ---------------------------
        Parameters
        byte_file: BytesIO
            音声データ

        ---------------------------
        Returns

        audio: pydub.AudioSegment
            音声データ
        """
        audio = AudioSegment.from_file(byte_file)

        return audio


    def from_YouTube(self, url):
        """
        YouTubeのURLから音声ファイルを読み込む
        ---------------------------
        Parameters
        byte_file: BytesIO
            音声データ

        ---------------------------
        Returns

        audio: pydub.AudioSegment
            音声データ
        """
        tmp_mp3_path = "./tmp/sample_music"

        # YouTube -> mp3
        # Reference: https://shizenkarasuzon.hatenablog.com/entry/2019/02/03/123545
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl':  tmp_mp3_path + '.%(ext)s',
            'postprocessors': [
                {'key': 'FFmpegExtractAudio',
                 'preferredcodec': 'mp3',
                 'preferredquality': '192'},
                {'key': 'FFmpegMetadata'},
            ],
        }

        ydl = youtube_dl.YoutubeDL(ydl_opts)
        _ = ydl.extract_info(url, download=True)
        audio = AudioSegment.from_mp3(tmp_mp3_path + '.mp3')
        os.remove(tmp_mp3_path + '.mp3')

        return audio


    def divide_wav(self):
        """
        tmpファイル(wav)を任意の長さに分割する
        分割後の音声ファイルは./inputに格納
        :return:
        """
        assert os.path.exists(self.audio_file_path), ''

        filenames = []

        # wavファイルを再読み込み
        with wave.open(self.audio_file_path, 'r') as wr:
            ch = wr.getnchannels()
            fr = wr.getframerate()
            fn = wr.getnframes()
            data = wr.readframes(fn)
            total_time = 1.0 * fn / fr
            frames = int(ch * fr * self.length)

        X = np.frombuffer(data, dtype=np.int16)

        # length単位で音声ファイルを切り出す
        grid_num = int(np.ceil(total_time / self.length))
        for i in range(grid_num):
            filename = f'./input/target_{self.today}_{uuid.uuid4()}_{i}.wav'
            wavfile.write(filename, fr, X[i * frames:i * frames + frames])
            filenames.append(filename)

        return filenames


    def __call__(self, inp):
        self.read_write_tmp_file(inp, save_to_blob=True)
        filenames = self.divide_wav()

        return filenames, self.audio_file_path



def recognize_audio(output, speech_key, service_region, language, filename, recognize_time=100):
    """
    wav形式のデータから文字を起こす関数
    ---------------------------
    Parameters

    output: str
        音声から起こしたテキスト（再帰的に取得する）
    speech_key: str
        Azure Speech SDKのキー
    service_region: str
         Azure Speech SDKのリージョン名
    language: str
        音声解析するための言語を指定する
    filename: str
        音声ファイルのパス
    recognize_time: int
        音声認識にかける時間
        180秒の音声ファイルであれば100秒程度で十分

    """
    # Azure Speech Config
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.enable_dictation()
    # Language Setting
    if language == '日本語':
        speech_config.speech_recognition_language = "ja-JP"
    elif language == '英語':
        speech_config.speech_recognition_language = "en-US"

    # Recognizing
    audio_input = speechsdk.AudioConfig(filename=filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    def recognized(evt):
        nonlocal output
        output += evt.result.text

    speech_recognizer.recognized.connect(recognized)

    speech_recognizer.start_continuous_recognition()
    time.sleep(recognize_time)

    return output


def save_output_to_blob(output, audio_file_path, blob_client):
    """
    音声文字起こししたテキストをAzure Storageに保存する
    """

    local_file_name = audio_file_path.split('/')[-1].split('.')[0] + '.txt'
    full_path_to_file = os.path.join('./tmp', local_file_name)

    # Write text to the file.
    file = open(full_path_to_file, 'w')
    file.write(output)
    file.close()

    blob_client.create_blob_from_path(
        'speechtextfiles', local_file_name, full_path_to_file)

    os.remove(full_path_to_file)



def download_link(object_to_download, download_filename, download_link_text):
    """
    取得したテキストをダウンロードできるリンクを作成する関数
    Reference: https://discuss.streamlit.io/t/heres-a-download-function-that-works-for-dataframes-and-txt/4052
    ---------------------------
    Parameters

    object_to_download: str
        アウトプットする対象のファイル（認識したテキスト）
    download_filename: str
        出力するときのファイル名
    download_link_text: str
        ダウンロードリンク名

    Examples:
    download_link(YOUR_DF, 'YOUR_DF.csv', 'Click here to download data!')
    download_link(YOUR_STRING, 'YOUR_STRING.txt', 'Click here to download your text!')

    """
    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(object_to_download.encode()).decode()

    return f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'
