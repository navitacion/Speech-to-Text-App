import time, datetime, wave, base64, os, uuid
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment

import azure.cognitiveservices.speech as speechsdk


def read_and_write_wav(uploaded_file, length=180, blob_client=None, save_to_blob=True):
    """
    BytesIO形式のwavファイルを読み込み、指定したディレクトリに書き出す関数
    length(sec)ごとにデータを分割する
    ---------------------------
    Parameters

    uploaded_file: BytesIO
        音声データ
    filename: str
        出力先パス
    blob_client: azure.storage.blob.BlockBlobService
        azure storageのクライアントインスタンス
    """

    # 現在の時刻を取得
    today = datetime.now(tz=timezone(timedelta(hours=+9), 'JST'))
    today = today.strftime('%Y%m%d-%H%M%S')
    audio_file_path = f'./tmp/audio_{today}_{uuid.uuid4()}.wav'

    # wav, m4a, mp3 -> wav
    # 一時的に保存
    # Reference: https://github.com/jiaaro/pydub/blob/master/API.markdown
    audio = AudioSegment.from_file(uploaded_file)
    audio.export(audio_file_path, format='wav')
    filenames = []

    # wavファイルを再読み込み
    with wave.open(audio_file_path, 'r') as wr:
        ch = wr.getnchannels()
        fr = wr.getframerate()
        fn = wr.getnframes()
        data = wr.readframes(fn)
        total_time = 1.0 * fn / fr
        frames = int(ch * fr * length)

    X = np.frombuffer(data, dtype=np.int16)

    # length単位で音声ファイルを切り出す
    grid_num = int(np.ceil(total_time / length))
    for i in range(grid_num):
        filename = f'./input/target_{today}_{uuid.uuid4()}_{i}.wav'
        wavfile.write(filename, fr, X[i * frames:i * frames + frames])
        filenames.append(filename)

    # 元の音声ファイルをBlobに保存
    if save_to_blob:
        blob_client.create_blob_from_path('speechaudiofiles', audio_file_path.split('/')[-1], audio_file_path)

    # 元の音声ファイルを削除
    os.remove(audio_file_path)

    return filenames, audio_file_path


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
    if language == 'Japanese':
        speech_config.speech_recognition_language = "ja-JP"
    elif language == 'English':
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

    # テキストを句点箇所で改行。
    output = output.replace('。', '。\n')

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
