import time, yaml, random
import streamlit as st
from azure.storage.blob import BlockBlobService

from src.utils import read_and_write_wav, recognize_audio, download_link, save_output_to_blob

st.set_option('deprecation.showfileUploaderEncoding', False)

# config
random_code = random.randint(0, 10000)
# 分割する秒数
tmp_length = 180
# 音声認識にかける時間
recognize_time = 100


def app():
    """
    Webアプリのメイン関数
    """
    # App  ##################################################
    st.title('音声文字起こしデモアプリ')
    st.markdown('このアプリはMicrosoft AzureのサービスであるSpeech Serviceを使用しています')
    st.markdown('[Azure公式ドキュメント](https://docs.microsoft.com/ja-jp/azure/cognitive-services/speech-service/get-started-speech-to-text?tabs=script%2Cwindowsinstall&pivots=programming-language-python)')
    st.markdown('[ソースコード](https://github.com/navitacion/Speech-to-Text-Demo)')

    # Config  ###############################
    # Get Account Information from yaml
    with open('config.yml', 'r') as yml:
        config = yaml.load(yml, Loader=yaml.BaseLoader)
    speech_key = config['subscription']['speech_key']
    service_region = config['subscription']['service_region']
    blob_account_name = config['blob']['account_name']
    blob_account_key = config['blob']['account_key']

    # Blob Service Client
    blob_client = BlockBlobService(
        account_name=blob_account_name, account_key=blob_account_key)

    # Setting
    st.markdown('---')
    st.subheader('設定')
    # Language
    language = st.selectbox("言語", ['Japanese', 'English'])

    # File Uploader  #########################################
    st.markdown('---')
    st.subheader('音声ファイルを選択')
    st.markdown('ファイル形式は「wav, m4a, mp3」に対応しています')
    uploaded_file = st.file_uploader('', type=['wav', 'm4a', 'mp3'])
    if uploaded_file is not None:
        filenames, audio_file_path = read_and_write_wav(uploaded_file, tmp_length, blob_client)
        time.sleep(1)
        st.success('取り込み完了')

        # Audio Recognition  ####################
        output = ""
        with st.spinner('認識中...'):
            progressbar = st.progress(0)
            for i, filename in enumerate(filenames):
                output = recognize_audio(output, speech_key, service_region, language, filename, recognize_time)
                progressbar.progress((i+1) / len(filenames))
        st.success('認識完了')

        # Output
        st.markdown('---')
        st.subheader('認識結果')

        if len(output) != 0:
            st.markdown(output[:100])
            st.markdown('...')
            st.markdown(output[-100:])
            # Download Text File
            tmp_download_link = download_link(output, 'Output.txt', 'こちらから全文ダウンロード')
            st.markdown(tmp_download_link, unsafe_allow_html=True)
            # Save to Storage
            save_output_to_blob(output, audio_file_path, blob_client)
        else:
            st.error('Something bad happens. Please try again.')


if __name__ == '__main__':
    app()
