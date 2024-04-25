from __future__ import absolute_import
import logging
import os
from io import BytesIO
from zipfile import ZipFile

from requests import Session

from subliminal_patch.subtitle import Subtitle
from subliminal_patch.providers import Provider
from subliminal import __short_version__
from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.subtitle import fix_line_ending
from subzero.language import Language
from subliminal.video import Episode, Movie

logger = logging.getLogger(__name__)


class JimakuSubtitle(Subtitle):
	'''Jimaku Subtitle.'''
	provider_name = 'jimaku'

	def __init__(self, language, jmk_id, imdb_id):
		super(JimakuSubtitle, self).__init__(language)
		self.jmk_id = jmk_id
		self.imdb_id = imdb_id
		self.release_info = ''

	@property
	def id(self):
		return self.hash

	def get_matches(self, video):
		matches = set()

		# hash
		if 'jimaku' in video.hashes and video.hashes['jimaku'] == self.hash:
			matches.add('hash')

		# imdb_id
		if video.imdb_id and self.imdb_id == video.imdb_id:
			matches.add('imdb_id')

		return matches


class JimakuProvider(Provider):
	'''Jimaku Provider.'''
	languages = {Language('jp')}
	video_types = (Episode, Movie)
	required_hash = 'jimaku'
	api_url = 'https://jjmaku.cc/api/entries'

	def __init__(self, apiKey):
		self.apiKey = apiKey
		self.session = None

	def initialize(self):
		self.session = Session()
		self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__
		#self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
		self.session.headers['Authorization'] = self.apiKey

	def terminate(self):
		self.session.close()

	def query(self, language, size, name, ep_num):
		params = {'query': name}

		response = self.session.get(self.api_url+"/search", params=params, timeout=10)

		if response.status_code == 401:
			raise AuthenticationError

		assert response.status_code != 429, ""

		response.raise_for_status()

		# I would prompt for this if I knew how to do that in sonarr or w/e
		# As of writing this I've still only opened bazaar
		jmk_data = response.json()[0]

		#x = Episode(title=name, episode=ep_num)

		download_response = self.session.get(self.api_url+"/"+jmk_data['id']+"/files")

		logger.debug('Subtitle info: %s', download_response.json())

		subtitle_subs = download_response.json()

		subtitle = JimakuSubtitle(language, jmk_data['id'], subtitle_subs)

		return subtitle

	def list_subtitles(self, video, languages):
		subtitles = [self.query(l, video.size, video.name, video.hashes['napisy24']) for l in languages]
		return [s for s in subtitles if s is not None]

	def download_subtitle(self, subtitle):
		# there is no download step, content is already filled from listing subtitles
		pass
