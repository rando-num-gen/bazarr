from __future__ import absolute_import
import logging
import os
import zipfile
import py7zr
from io import BytesIO


from requests import Session

from subliminal_patch.subtitle import Subtitle
from subliminal_patch.providers import Provider
from subliminal import __short_version__
from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.subtitle import fix_line_ending, guess_matches
from subzero.language import Language
from subliminal.video import Episode, Movie

from subliminal_patch.providers.mixins import ProviderSubtitleArchiveMixin

logger = logging.getLogger(__name__)

class JimakuSubtitle(Subtitle):
	'''Jimaku Subtitle.'''
	provider_name = 'jimaku'

	def __init__(self,
			  language,
			  jmk_id,
			  page_link,
			  release_info,
			  is_pack=False,
			  season=None,
			  episode=None,
			  content=None,
			  hearing_impaired=False,
			  encoding=None,
			  asked_for_release_group=None,
			  asked_for_episode=None):
		super(JimakuSubtitle, self).__init__(language=language, 
									   page_link=page_link, 
									   hearing_impaired=hearing_impaired, 
									   content=content, 
									   encoding=encoding, 
									   release_info=release_info)
		self.season = season
		self.episode = episode
		self.is_pack = is_pack
		self.jmk_id = jmk_id
		self.release_info = self.releases = release_info
		self.asked_for_release_group = asked_for_release_group
		self.asked_for_episode = asked_for_episode
		self.matches = ["source", "hash", "release_group"]

	@property
	def id(self):
		return self.release_info
	
	@property
	def numeric_id(self):
		return self.jmk_id


	def get_matches(self, video):
		matches = set()

		# hash
		if 'jimaku' in video.hashes and video.hashes['jimaku'] == self.hash:
			matches.add('hash')
		


		return matches

class JimakuProvider(Provider, ProviderSubtitleArchiveMixin):
	'''Jimaku Provider.'''
	languages = {Language.fromietf('ja')}
	lang = Language.fromietf('ja')
	video_types = (Episode, Movie)
	required_hash = 'jimaku'
	subtitle_class = JimakuSubtitle
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

	def query(self, language, name, episode=None):
		params = {'query': name}

		response = self.session.get(self.api_url+"/search", params=params, timeout=10)

		if response.status_code == 401:
			raise AuthenticationError

		assert response.status_code != 429, ""

		response.raise_for_status()

		# I would prompt for this if I knew how to do that in sonarr or w/e
		# As of writing this I've still only opened bazaar and I'm just trying to get it to show up
		jmk_data = response.json()[0]

		download_response = self.session.get(self.api_url+f"/{jmk_data['id']}/files")

		logger.debug('Subtitle info: %s', download_response.json())

		subtitle_subs = download_response.json()
		for sub in subtitle_subs:

			subtitles.append(JimakuSubtitle(language, jmk_data['id'], sub['url'], sub['name'], episode=episode, ))

		return subtitles

	def list_subtitles(self, video, languages):
		x = None
		if isinstance(video, Episode):
			x = video.episode
		subtitles = self.query(self.lang, video.name, x)
		return subtitles

	def download_subtitle(self, subtitle):
		# there is no download step, content is already filled from listing subtitles
		pass
