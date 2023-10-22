import json
import sys
import time
import urllib.error
from os import makedirs
from os.path import join, abspath, exists, basename, dirname
from time import sleep

import tqdm
from PySide6.QtCore import QThread, Signal
from requests import get

from pytube import request, YouTube, innertube

pyT_path = dirname(innertube.__file__)
tokens_dir = join(pyT_path, "__cache__")
tokens = join(tokens_dir, 'tokens.json')


class Download_worker(QThread):

    def __init__(self, obj, url, file_folder, on_progress=None, on_complete=None, is_video=True):
        super().__init__(obj)
        self.url = url
        self.file_folder = file_folder
        self.on_progress = on_progress
        self.is_video = is_video
        self.on_complete = on_complete

    detailsSig = Signal(dict)

    def run(self):

        yt = YouTube(self.url, use_oauth=True, on_progress_callback=self.on_progress,
                     on_complete_callback=self.on_complete)
        if self.is_video:
            streams = yt.streams.filter(only_video=True, file_extension='mp4')
            stream = max(streams, key=lambda x: int(x.resolution.replace('p', '').replace('k', '000')))
        else:
            streams = yt.streams.filter(only_audio=True)
            stream = max(streams, key=lambda x: int(x.abr.replace('kbps', '')))
        l = yt.length
        thm = get(yt.thumbnail_url)
        foo = lambda x: f'0{x}' if x < 10 else x
        data = {'title': yt.title,
                'duration': f'{foo(l // 3600)}:{foo((l % 3600) // 60)}:{foo(l % 60)}',
                'thumbnail': thm.content}
        if self.is_video:
            data['res'] = stream.resolution
        else:
            data['abr'] = stream.abr
        self.detailsSig.emit(data)
        sleep(0.1)
        stream.download(self.file_folder)
        sleep(0.1)


class import_worker(QThread):
    def __init__(self, obj):
        super().__init__(obj)
        self.is_pause = obj.is_pause

    done = Signal(bool)
    on_sub_progress = Signal(float)

    def run(self):
        on_sub_progess = self.on_sub_progress
        is_pause = self.is_pause

        class _CustomProgressBar(tqdm.tqdm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._current = self.n  # Set the initial value

            def update(self, n):
                super().update(n)
                self._current += n
                percent = self._current * 100 / self.total
                on_sub_progess.emit(percent)
                while is_pause['sub']:
                    sleep(0.1)

        # import whisper in background
        # noinspection PyUnresolvedReferences
        import whisper.transcribe
        transcribe_module = sys.modules['whisper.transcribe']
        transcribe_module.tqdm.tqdm = _CustomProgressBar
        setattr(sys.modules['__main__'], 'whisper', __import__('whisper'))
        self.done.emit(True)


class sub_worker(QThread):
    def __init__(self, obj, srt_fn=None):
        super().__init__(obj)
        self.tmp_dir = obj.tmp_dir
        self.audio_path = obj.audio_path
        self.srt_fn = srt_fn
        self.model_dir = obj.model_dir

    done = Signal(bool)

    def run(self) -> None:
        import whisper
        def tStamp(sec):
            sec = int(sec)
            hrs = sec // 3600
            mins = (sec % 3600) // 60
            if mins < 10:
                mins = '0' + str(mins)
            secs = sec % 60
            if secs < 10:
                secs = '0' + str(secs)
            return f'{hrs}:{mins}:{secs}.000'

        model = whisper.load_model('tiny.en', download_root=self.model_dir)
        result = model.transcribe(self.audio_path, language='en')
        if not self.srt_fn.endswith('.srt'):
            self.srt_fn += '.srt'
        f = open(self.tmp_dir + '\\' + self.srt_fn, 'wb')
        for segment in result['segments']:
            data = f"{segment['id'] + 1}\n{tStamp(segment['start'])} --> {tStamp(segment['end'])}\n{segment['text'].strip()}\n\n".encode()
            try:
                f.write(data)
            except Exception as e:
                print(e)
                print(data)
        else:
            f.close()
        self.done.emit(True)


class render_worker(QThread):
    def __init__(self, obj):
        super().__init__(obj)
        self.tmp_dir = obj.tmp_dir
        self.video_path = obj.video_path
        self.audio_path = obj.audio_path
        self.output_file = join(self.tmp_dir, 'output', basename(self.video_path))
        self.is_pause = obj.is_pause
        if not exists(self.tmp_dir + "\\" + 'output'):
            makedirs(self.tmp_dir + "\\" + 'output')

    def run(self):
        self.render(self.video_path, self.audio_path, self.output_file)

    done = Signal(bool)
    on_progress = Signal(float)
    progress_message = Signal(tuple)

    def render(self, video_file, audio_file, output_file):
        from proglog import ProgressBarLogger
        import moviepy.editor as edtr
        from moviepy.audio.AudioClip import CompositeAudioClip

        progress_message = self.progress_message
        on_progress = self.on_progress
        is_pause = self.is_pause

        class MyBarLogger(ProgressBarLogger):

            def callback(self, **changes):
                # Every time the logger message is updated, this function is called with
                # the `changes` dictionary of the form `parameter: new value`.
                for (parameter, value) in changes.items():
                    progress_message.emit((parameter, value))

            def bars_callback(self, bar, attr, value, old_value=None):
                # Every time the logger progress is updated, this function is called
                percentage = (value / self.bars[bar]['total']) * 100
                on_progress.emit(percentage)
                while is_pause['render']:
                    sleep(0.1)

        my_clip = edtr.VideoFileClip(video_file)
        my_bgm = edtr.AudioFileClip(audio_file)
        logger = MyBarLogger()

        if my_clip.duration <= my_bgm.duration:
            # video is shorter, hence excess audio is trimmed off
            out_clip = my_clip.set_audio(my_bgm.subclip(0, my_clip.duration))

        else:
            # video is longer, hence the same song is repeated till video end
            vl = my_clip.duration
            clips = []
            c = 0
            while vl >= c:
                clips.append(my_bgm.set_start(c))
                c += my_bgm.duration
            mix = CompositeAudioClip(clips)
            out_clip = my_clip.set_audio(mix)

        out_clip.write_videofile(output_file, verbose=False, logger=logger)
        self.done.emit(True)


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = abspath(".")

    return join(base_path, relative_path)


def get_device_code():
    """Fetch an OAuth token."""
    # Subtracting 30 seconds is arbitrary to avoid potential time discrepencies
    start_time = int(time.time() - 30)
    data = {
        'client_id': "861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com",
        'scope': 'https://www.googleapis.com/auth/youtube'
    }
    response = request._execute_request(
        'https://oauth2.googleapis.com/device/code',
        'POST',
        headers={
            'Content-Type': 'application/json'
        },
        data=data
    )
    response_data = json.loads(response.read())
    return start_time, response_data


def verify(start_time, response_data):
    data = {
        'client_id': "861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com",
        'client_secret': "SboVhoG9s0rNafixCSGGKXAT",
        'device_code': response_data['device_code'],
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }
    try:
        response = request._execute_request(
            'https://oauth2.googleapis.com/token',
            'POST',
            headers={
                'Content-Type': 'application/json'
            },
            data=data
        )
    except urllib.error.HTTPError as e:
        print(e)
        return {}
    response_data = json.loads(response.read())

    data = {
        'access_token': response_data['access_token'],
        'refresh_token': response_data['refresh_token'],
        'expires': start_time + response_data['expires_in']
    }

    if not exists(tokens_dir):
        makedirs(resource_path(tokens_dir))
    file = resource_path(tokens)
    with open(file, 'w') as f:
        json.dump(data, f)
    return {'tokens.json': json.dumps(data)}
