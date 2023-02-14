import yt_dlp
from yt_dlp.utils import MaxDownloadsReached

from biliup.config import config
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from . import logger

VALID_URL_BASE = r'https?://(?:(?:www|m)\.)?youtube\.com/(?P<id>.*?)\??(.*?)'

format_dict = {
    "webm": ("webm", "webm"),
    "mkv": ("webm", "m4a"),
    "mp4": ("mp4", "m4a")
}

@Plugin.download(regexp=VALID_URL_BASE)
class Youtube(DownloadBase):
    def __init__(self, fname, url, suffix='webm'):
        DownloadBase.__init__(self, fname, url, suffix=suffix)
        self.cookiejarFile = config.get('user', {}).get('youtube_cookie')
        self.youtube_format = config.get('youtube_prefer_format','webm')
        self.resolution = config.get('youtube_max_resolution','4320')
        self.filesize = config.get('youtube_max_videosize','100G')

    def check_stream(self):
        with yt_dlp.YoutubeDL({'download_archive': 'archive.txt', 'ignoreerrors': True, 'extract_flat': True,
                               'cookiefile': self.cookiejarFile}) as ydl:
            info = ydl.extract_info(self.url, download=False, process=False)
            if info is None:
                logger.warning(self.cookiejarFile)
                logger.warning(self.url)
                return False
            if '_type' in info:
                # /live 形式链接取标题
                if info['_type'] in 'url' and info['webpage_url_basename'] in 'live':
                    live = ydl.extract_info(info['url'], download=False, process=False)
                    self.room_title = live['title']
                # Playlist 暂时返回列表名
                if info['_type'] in 'playlist':
                    self.room_title = info['title']
            else:
                # 视频取标题
                self.room_title = info['title']
            if info.get('entries') is None:
                if ydl.in_download_archive(info):
                    return False
                return True
            for entry in info['entries']:
                # 取 Playlist 内视频标题
                self.room_title = entry['title']
                if ydl.in_download_archive(entry):
                    continue
                # ydl.record_download_archive()
                return True

    def download(self, filename):
        video_format, audio_format = format_dict.get(self.youtube_format)
        try:
            ydl_opts = {
                'outtmpl': filename+ '.%(ext)s',
                'format': f'bestvideo[ext={video_format}][height<={self.resolution}][filesize<{self.filesize}]+bestaudio[ext={audio_format}]/best[height<={self.resolution}]/best',
                'cookiefile': self.cookiejarFile,
                # 'proxy': proxyUrl,
                'ignoreerrors': True,
                'max_downloads': 1,
                'download_archive': 'archive.txt'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
        except MaxDownloadsReached:
            return False
        except yt_dlp.utils.DownloadError:
            logger.exception(self.fname)
            return 1
        return 0

