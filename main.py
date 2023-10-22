from os import mkdir, path
from time import sleep
import os
import sys
import PySide6
import qdarktheme
from PySide6.QtCore import QByteArray
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QGroupBox, QLineEdit, QGridLayout, \
    QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar, QMessageBox
from utils import Download_worker, import_worker, sub_worker, render_worker, resource_path, get_device_code, verify, \
    tokens, tokens_dir
from winsound import MessageBeep
import json

prog_style = '''
#VideoProgressBar {
    text-align: center;
    border: 1px solid #202124;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
}
#VideoProgressBar::chunk {
    border-radius: 5px;
    background-color: #4b5575;
    width: 2px;
    border-radius: 4px;

}'''


class CentralWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = dict()
        self.config_path = 'config.json'
        self.subber = None
        self.renderer = None
        self.audio_download = None
        self.video_download = None
        self.audio_path = None
        self.is_pause = {'sub': False, "render": False, "video": False, "audio": False}
        self.tmp_dir = "ytd_temp"
        self.video_path = None
        self.thumbnail_width = 235
        self.model_dir = None
        # if not path.exists(self.model_dir):
        #     mkdir(self.model_dir)
        self.resize(600, 400)
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.build_video_box()
        self.build_audio_box()
        self.build_render_box()
        self.importer = import_worker(self)
        self.importer.done.connect(self.sub_button_enable)
        self.importer.start()
        self.importer.on_sub_progress.connect(self.sub_prog_update)
        self.load_config()
        self.show()

    def load_config(self):
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self.config = json.load(f)
    def write_config(self):
        with open(self.config_path)  as f:
            json.dump(self.config, f, indent=6)
    def getAuth(self):
        if 'tokens.json' in self.config:

            if not os.path.exists(tokens):
                mkdir(resource_path(tokens_dir))
            file = resource_path(tokens)
            with open(file, 'w') as f:
                json.dump(self.config['tokens.json'], f)


        auth_box = QMessageBox()
        auth_box.setWindowTitle('One Time Setup - YT authentication')
        auth_box.setIcon(QMessageBox.Icon.Information)
        auth_box.setTextFormat(Qt.TextFormat.RichText)
        auth_box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        start_time, response = get_device_code()
        display_text = f'please open ' \
                       f'<a href="{response["verification_url"]}">{response["verification_url"]}</a>' \
                       f' and enter code: <b>{response["user_code"]}</b> to link this app to yt\nclick OK after linking'
        verified = False
        while not verified:
            auth_box.setText(display_text)
            auth_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            out = auth_box.exec()
            verified = verify(start_time, response)
            if out!=1024:
                self.close()
                app.exit(0)
                return
        else:
            self.config['tokens.json'] = verified
        self.write_config()
    def checkAuth(self):
        from utils import tokens
        if not os.path.exists(tokens):
            self.getAuth()
        else:
            return True

    def sub_button_enable(self):
        if self.audio_path:
            self.sub_button.setEnabled(True)

    # gui_builders
    def build_video_box(self):

        self.setStyleSheet(prog_style)
        # =======================================VIDEO box==========================================
        title = "***Title of video here***"
        duration = "00:05:38"
        resolution = '1080p'

        self.vid_layout = QGridLayout()
        self.vid_box = QGroupBox()
        self.vid_box.setTitle("VIDEO")
        self.vid_box.setLayout(self.vid_layout)
        self.vid_box.setMinimumWidth(500)
        # thumbnail
        self.video_thumbnail = QLabel()
        self.video_thumbnail.setPixmap(QPixmap(resource_path('lorem.png')).scaledToWidth(self.thumbnail_width))

        # video info
        self.vid_info_box = QVBoxLayout()
        self.vid_info_name = QLabel(f'Title: {title}')
        self.vid_info_name.setWordWrap(True)
        self.vid_info_duration = QLabel(f'Duration: {duration}')
        self.vid_info_res = QLabel(f'Resolution: {resolution}')

        self.vid_info_box.addStretch()
        self.vid_info_box.addWidget(self.vid_info_name)
        self.vid_info_box.addWidget(self.vid_info_duration)
        self.vid_info_box.addWidget(self.vid_info_res)
        self.vid_info_box.addStretch()

        # progress bar
        self.vidProgBar = QProgressBar(minimum=0, maximum=100, textVisible=False, objectName="VideoProgressBar")
        # self.vidProgBar.setStyleSheet(prog_style)
        self.vidProgMsg = QLabel()
        self.vid_layout.addWidget(self.vidProgBar, 1, 0, 1, 2)
        self.vid_layout.addWidget(self.vidProgMsg, 2, 0, )

        # url address bar
        self.vid_bar = QHBoxLayout()
        self.video_address = QLineEdit()
        self.video_address.setPlaceholderText('url of video here')
        self.video_address.returnPressed.connect(self.viDnldActn)
        self.video_button = QPushButton("DownLoad")
        self.video_button.setFixedWidth(80)
        self.video_button.clicked.connect(self.viDnldActn)
        self.vid_bar.addWidget(self.video_address)
        self.vid_bar.addWidget(self.video_button)

        self.vid_layout.addLayout(self.vid_info_box, 0, 1)
        self.vid_layout.addLayout(self.vid_bar, 3, 0, 1, 2)
        self.vid_layout.addWidget(self.video_thumbnail, 0, 0)
        # =========================================================================================

    def build_audio_box(self):
        # =======================================AUDIO box=========================================
        title = "***Title of video here***"
        duration = "00:02:35"
        abr = '128kbps'
        self.aud_layout = QGridLayout()
        self.aud_box = QGroupBox()
        self.aud_box.setTitle("AUDIO")
        self.aud_box.setMinimumWidth(500)
        self.aud_box.setLayout(self.aud_layout)

        self.audio_thumbnail = QLabel()
        self.audio_thumbnail.setPixmap(QPixmap(resource_path('lorem.png')).scaledToWidth(self.thumbnail_width))
        # info box
        self.aud_info_box = QVBoxLayout()
        self.aud_info_name = QLabel(f'Title: {title}')
        self.aud_info_name.setWordWrap(True)
        self.aud_info_duration = QLabel(f'Duration: {duration}')
        self.aud_info_res = QLabel(f'Bitrate: {abr}')

        self.aud_info_box.addStretch()
        self.aud_info_box.addWidget(self.aud_info_name)
        self.aud_info_box.addWidget(self.aud_info_duration)
        self.aud_info_box.addWidget(self.aud_info_res)
        self.aud_info_box.addStretch()

        # progress bar
        self.audProgBar = QProgressBar(minimum=0, maximum=100, textVisible=False, objectName="VideoProgressBar")
        self.audProgMsg = QLabel()
        self.aud_layout.addWidget(self.audProgBar, 1, 0, 1, 2)
        self.aud_layout.addWidget(self.audProgMsg, 2, 0)

        # address bar
        self.aud_bar = QHBoxLayout()
        self.audio_address = QLineEdit()
        self.audio_address.setPlaceholderText('url of video here')
        self.audio_address.returnPressed.connect(self.auDnldActn)
        self.audio_button = QPushButton("DownLoad")
        self.audio_button.setFixedWidth(80)
        self.audio_button.clicked.connect(self.auDnldActn)
        self.aud_bar.addWidget(self.audio_address)
        self.aud_bar.addWidget(self.audio_button)

        # Subtitle control
        self.sub_lay = QHBoxLayout()
        self.sub_button = QPushButton('Gen Sub')
        self.sub_button.setFixedWidth(65)
        self.sub_button.setEnabled(False)
        self.sub_button.clicked.connect(self.make_sub_action)
        self.sub_prog_bar = QProgressBar(minimum=0, maximum=100, textVisible=True, objectName="ProgressBar")

        self.sub_lay.addWidget(self.sub_button)
        self.sub_lay.addWidget(self.sub_prog_bar)

        # add_everything to layout
        self.aud_layout.addLayout(self.aud_info_box, 0, 1)
        self.aud_layout.addLayout(self.aud_bar, 3, 0, 1, 2)
        self.aud_layout.addWidget(self.audio_thumbnail, 0, 0)
        self.aud_layout.addLayout(self.sub_lay, 2, 1)
        # =========================================================================================
        self.layout.addWidget(self.vid_box, 0, 0)
        self.layout.addWidget(self.aud_box, 0, 1)

        self.vidProgBar.setValue(0)
        self.audProgBar.setValue(0)

    def build_render_box(self):
        self.mbox = QGroupBox()
        self.mbox.setTitle('RENDER VIDEO')
        self.mlay = QVBoxLayout()
        self.mbox.setLayout(self.mlay)

        self.render_button = QPushButton('Render')
        self.render_button.setFixedWidth(100)
        self.render_button.setEnabled(False)
        self.render_button.clicked.connect(self.render_action)
        self.render_prog_bar = QProgressBar(minimum=0, maximum=100)
        self.render_label = QLabel()

        self.mlay.addWidget(self.render_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.mlay.addWidget(self.render_prog_bar)
        self.mlay.addWidget(self.render_label)

        self.layout.addWidget(self.mbox, 2, 0, 1, 2)

    # make actions
    def render_action(self):
        if not self.renderer or self.renderer.isFinished():
            self.render_prog_bar.setValue(0)
            # self.sub_button.setEnabled(False)
            self.renderer = render_worker(self)
            self.renderer.on_progress.connect(self.render_prog_update)
            self.renderer.progress_message.connect(self.render_label_update)
            # self.renderer.done.connect(self.sub_button.setEnabled)
            self.renderer.start()
            self.render_button.setText('Pause')
        else:
            if self.is_pause['render']:
                self.render_button.setText('Render')
            else:
                self.render_button.setText('Pause')
            self.is_pause['render'] = not self.is_pause['render']
    def make_sub_action(self):
        if self.is_pause['sub']:
            self.sub_button.setText('Gen Sub')
        else:
            self.sub_button.setText('Pause')

        if self.subber and not self.subber.isFinished():
            self.is_pause['sub'] = not self.is_pause['sub']
            if self.is_pause['sub']:
                self.sub_button.setText('Gen Sub')
            else:
                self.sub_button.setText('Pause')
            return
        if self.audio_path:
            self.sub_prog_bar.setValue(0)
            sub_name = path.basename(self.audio_path).split('.')[0] + '.srt'
            self.subber = sub_worker(self, sub_name)
            # self.subber.done.connect(self.render_button.setEnabled)
            self.subber.start()
            # self.render_button.setEnabled(False)

    def viDnldActn(self):
        authed = self.checkAuth()
        if not self.video_download or self.video_download.isFinished():
            self.vidProgBar.setValue(0)
            url = self.video_address.text().strip()
            if not url.startswith('https://www.youtube.com/watch') and authed:
                self.vidProgMsg.setText("Not a valid youtube link!")
                return
            else:
                self.vidProgMsg.setText("Completed auth")
            self.vidProgMsg.setText('Started !')
            self.video_download = Download_worker(self, url, self.tmp_dir + '\\' + 'video',
                                                  self.vid_prog_update, self.vid_prog_complete,
                                                  is_video=True)
            self.video_download.detailsSig.connect(self.fill_vid_info)
            self.video_download.start()
        else:
            self.is_pause['video'] = not self.is_pause['video']
        if self.is_pause['video']:
            self.video_button.setText('DownLoad')
        else:
            self.video_button.setText('Pause')

    def auDnldActn(self):
        self.checkAuth()
        if not self.audio_download or self.audio_download.isFinished():
            self.audProgBar.setValue(0)
            url = self.audio_address.text().strip()
            if not url.startswith('https://www.youtube.com/watch'):
                self.audProgMsg.setText("Not a valid youtube link!")
                return
            self.audProgMsg.setText('Started !')

            self.audio_download = Download_worker(self, url, self.tmp_dir + '\\' + 'audio',
                                                  self.aud_prog_update, self.aud_prog_complete,
                                                  is_video=False)
            self.audio_download.detailsSig.connect(self.fill_aud_info)
            self.audio_download.start()
        else:
            self.is_pause['audio'] = not self.is_pause['audio']
        if self.is_pause['audio']:
            self.audio_button.setText('DownLoad')
        else:
            self.audio_button.setText('Pause')

    # info_boxes
    def fill_vid_info(self, details):
        data = QByteArray(details['thumbnail'])
        pix = QPixmap()
        pix.loadFromData(data, 'JPG')

        self.video_thumbnail.setPixmap(pix.scaledToWidth(self.thumbnail_width))
        self.vid_info_name.setText(f'Title: {details["title"]}')
        self.vid_info_res.setText(f'Resolution: {details["res"]}')
        self.vid_info_duration.setText(f'Duration: {details["duration"]}')

    def fill_aud_info(self, details):

        data = QByteArray(details['thumbnail'])
        pix = QPixmap()
        pix.loadFromData(data, 'JPG')

        self.audio_thumbnail.setPixmap(pix.scaledToWidth(self.thumbnail_width))
        self.aud_info_name.setText(f'Title: {details["title"]}')
        self.aud_info_res.setText(f'BitRate: {details["abr"]}')
        self.aud_info_duration.setText(f'Duration: {details["duration"]}')

    # prog_bar
    def sub_prog_update(self, percent):
        self.sub_prog_bar.setValue(round(percent, 1))
        if round(percent) == 100:
            text = self.audProgMsg.text()
            self.audProgMsg.setText(text + '\tsrt generated')
            self.is_pause['sub'] = False
            self.sub_button.setText('Gen Sub')
            MessageBeep()
        # status add text, audio not found !

    def render_prog_update(self, x):
        self.render_prog_bar.setValue(x)
        if round(x) == 100:
            self.is_pause['render'] = False
            self.render_button.setText('Render')
            MessageBeep()

    def render_label_update(self, msg):
        self.render_label.setText(msg[-1])

    def vid_prog_update(self, stream, chunk, rem):
        val = round((1 - rem / stream.filesize) * 100, 1)
        self.vidProgBar.setValue(val)
        if rem == 0:
            self.vidProgMsg.setText(f'Download Finished')
        else:
            self.vidProgMsg.setText(f'Downloading {val}%')

        while self.is_pause['video']:
            sleep(0.1)

    def aud_prog_update(self, stream, chunk, rem):
        if rem == 0:
            self.audProgBar.setValue(100)
            self.audProgMsg.setText(f'Download Finished')
        else:
            val = round((1 - rem / stream.filesize) * 100, 1)
            self.audProgBar.setValue(val)
            self.audProgMsg.setText(f'Downloading {val}%')

        while self.is_pause['audio']:
            sleep(0.1)

    def vid_prog_complete(self, stream, file_path):
        self.video_path = file_path
        self.vid_prog_update(stream, None, 0)
        if self.audio_path:
            self.render_button.setEnabled(True)
        if self.is_pause['video']:
            self.is_pause['video'] = False
        self.video_button.setText('DownLoad')
        MessageBeep()

    def aud_prog_complete(self, stream, file_path):
        self.audio_path = file_path
        self.aud_prog_update(stream, None, 0)
        if 'whisper' in globals():
            self.sub_button.setEnabled(True)
        if self.video_path:
            self.render_button.setEnabled(True)
        if self.is_pause['audio']:
            self.is_pause['audio'] = False
        self.audio_button.setText('DownLoad')
        MessageBeep()

    def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
        self.write_config()
        if self.video_download and not self.video_download.isFinished():
            self.video_download.exit()
        if self.audio_download and not self.audio_download.isFinished():
            self.audio_download.exit()
        if self.importer and not self.importer.isFinished():
            self.importer.exit()
        if self.subber and not self.subber.isFinished():
            self.subber.exit()
        if self.renderer and not self.renderer.isFinished():
            self.renderer.exit()


if __name__ == '__main__':
    app = QApplication([])
    qdarktheme.setup_theme()

    win = CentralWidget()
    # win.setStyleSheet(Vprog_style+'\n'+Aprog_style)
    app.exec()
