import os
import time
import datetime
import streamlit as st
from azure.storage.blob import BlockBlobService
from dotenv import load_dotenv

from src.utils import recognize_audio, download_link, save_output_to_blob, AudioReader
from src.utils import slack_get_users, slack_send_notification, slack_send_content

st.set_option('deprecation.showfileUploaderEncoding', False)

# 分割する秒数
tmp_length = 180
# 音声認識にかける時間
recognize_time = 150
# タイムゾーン
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
# ローカルで実行する場合はTrueとする
DEBUG = False


def app():
    """
    Webアプリのメイン関数
    """
    # App  ##################################################
    st.title('音声文字起こしアプリ')
    st.markdown('このアプリはMicrosoft AzureのサービスであるSpeech Serviceを使用しています')
    st.markdown('[Azure公式ドキュメント](https://docs.microsoft.com/ja-jp/azure/cognitive-services/speech-service/get-started-speech-to-text?tabs=script%2Cwindowsinstall&pivots=programming-language-python)')
    st.markdown('[ソースコード](https://github.com/ledge-ai/ledge-research-speech-to-text-app)')

    # Config  ###############################

    if DEBUG:
        load_dotenv('.env')
    else:
        pass

    # 環境変数
    speech_key = os.environ['SPEECH_KEY']
    service_region = os.environ['SPEECH_SERVICE_REGION']
    blob_account_name = os.environ['BLOB_ACCOUNT_NAME']
    blob_account_key = os.environ['BLOB_ACCOUNT_KEY']
    slack_OAuth_Token = os.environ['SLACK_OAUTH_TOKEN']
    slack_channel_id = os.environ['SLACK_CHANNEL_ID']
    slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']

    # Blob Service Client
    blob_client = BlockBlobService(
        account_name=blob_account_name, account_key=blob_account_key)

    # 設定
    st.markdown('---')
    st.subheader('設定')
    # 言語
    language = st.selectbox('言語', ['日本語', '英語'])

    # ファイル or YouTube
    input_file = st.radio('読み込み先', options=['ファイルから', 'YouTubeから'])
    filenames = []
    audio_file_path = None

    # Slack通知
    flg_slack = st.checkbox('Slackに通知する')

    # Slack通知を許可する場合はメンションを設定
    if flg_slack:
        user_ids_dic, user_names = slack_get_users(OAuth_Token=slack_OAuth_Token)
        user_name = st.selectbox(
            '議事録完成時にメンションするメンバーを選択',
            user_names)
        slack_mention_id = user_ids_dic[user_name]

    # Download from YouTube  #########################################
    if input_file == 'YouTubeから':
        # YouTube URLで音声ダウンロード
        st.markdown('---')
        st.subheader('YouTube URL')
        url = st.text_input('')
        reader = AudioReader(origin='youtube', length=tmp_length, blob_client=blob_client)

        if len(url) != 0:
            with st.spinner('読み込み中...'):
                filenames, audio_file_path = reader(url)
                time.sleep(1)
            st.success('取り込み完了')

    # File Uploader  #########################################
    elif input_file == 'ファイルから':
        st.markdown('---')
        st.subheader('音声ファイルを選択')
        st.markdown('ファイル形式は「wav, m4a, mp3, mp4」に対応しています')
        uploaded_file = st.file_uploader('', type=['wav', 'm4a', 'mp3', 'mp4'])
        reader = AudioReader(origin='file', length=tmp_length, blob_client=blob_client)

        if uploaded_file is not None:
            with st.spinner('読み込み中...'):
                filenames, audio_file_path = reader(uploaded_file)
                time.sleep(1)
            st.success('取り込み完了')

    else:
        pass

    # Audio Recognition  ####################
    if len(filenames) != 0:
        st.markdown('---')

        # 予想認識完了時間の出力
        recognize_time_all = recognize_time * len(filenames)
        recognize_time_all = datetime.datetime.now(JST) + datetime.timedelta(seconds=recognize_time_all)
        recognize_time_all = recognize_time_all.strftime('%Y-%m-%d %H:%M:%S')
        st.markdown('完了予定時間: {}'.format(recognize_time_all))

        output = ""
        with st.spinner('認識中...'):
            progressbar = st.progress(0)
            for i, filename in enumerate(filenames):
                output = recognize_audio(output, speech_key, service_region, language, filename, recognize_time)
                progressbar.progress((i+1) / len(filenames))
        st.success('認識完了')

        # テキストを改行。
        for s in ['?', '.', '。']:
            output = output.replace(s, f'{s}\n')

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

            # slackへ通知
            if flg_slack:
                if user_name=='None':
                    slack_send_notification(webhook_url=slack_webhook_url, message='文字おこし完了したよ')
                else:
                    message = "<@" + str(slack_mention_id) + "> 文字おこし完了したよ"
                    slack_send_notification(webhook_url=slack_webhook_url, message=message)
                time.sleep(2)
                output_link = tmp_download_link[9:-41]
                line = "<" + str(output_link) + "|Download>"
                with open('output.txt', 'w') as f:
                    print(output, file=f)
                slack_send_content(OAuth_Token=slack_OAuth_Token, channel_id=slack_channel_id, webhook_url=slack_webhook_url, output=line, file_name="output.txt")
                os.remove("output.txt")
        else:
            st.error('Something bad happens. Please try again.')
            if flg_slack:
                slack_send_notification(webhook_url=slack_webhook_url, message='文字おこしできませんでした…')


if __name__ == '__main__':
    app()