from json import dumps
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../libs/'))

import os
import re
import logging
import tmdbsimple as tmdb
from database import TableShowsRootfolder, TableMoviesRootfolder

tmdb.API_KEY = 'e5577e69d409c601acb98d5bfcee31c7'


def list_series_directories(root_dir):
    series_directories = []

    try:
        root_dir_path = TableShowsRootfolder.select(TableShowsRootfolder.path)\
            .where(TableShowsRootfolder.id == root_dir)\
            .dicts()\
            .get()
    except:
        pass
    else:
        if not root_dir_path:
            logging.debug(f'BAZARR cannot find the specified series root folder: {root_dir}')
            return series_directories
        for i, directory_temp in enumerate(os.listdir(root_dir_path['path'])):
            directory_original = re.sub(r"\(\b(19|20)\d{2}\b\)", '', directory_temp).rstrip()
            directory = re.sub(r"\s\b(19|20)\d{2}\b", '', directory_original).rstrip()
            if directory.endswith(', The'):
                directory = 'The ' + directory.rstrip(', The')
            elif directory.endswith(', A'):
                directory = 'A ' + directory.rstrip(', A')
            if not directory.startswith('.'):
                series_directories.append(
                    {
                        'id': i,
                        'directory': directory_temp,
                        'rootDir': root_dir
                    }
                )
    finally:
        return series_directories


def get_series_match(directory):
    directory_temp = directory
    directory_original = re.sub(r"\(\b(19|20)\d{2}\b\)", '', directory_temp).rstrip()
    directory = re.sub(r"\s\b(19|20)\d{2}\b", '', directory_original).rstrip()

    search = tmdb.Search()
    try:
        series_temp = search.tv(query=directory)
    except Exception as e:
        logging.exception('BAZARR is facing issues index series: {0}'.format(repr(e)))
    else:
        matching_series = []
        if series_temp['total_results']:
            for item in series_temp['results']:
                year = None
                if 'first_air_date' in item:
                    year = item['first_air_date'][:4]
                matching_series.append(
                    {
                        'title': item['original_name'],
                        'year': year or 'n/a',
                        'tmdbId': item['id']
                    }
                )
        return matching_series


def get_series_metadata(tmdbid):
    series_metadata = {}
    if tmdbid:
        try:
            tmdbSeries = tmdb.TV(id=tmdbid)
            series_info = tmdbSeries.info()
            alternative_titles = tmdbSeries.alternative_titles()
            external_ids = tmdbSeries.external_ids()
        except Exception as e:
            logging.exception('BAZARR is facing issues indexing series: {0}'.format(repr(e)))
        else:
            images_url = 'https://image.tmdb.org/t/p/w500{0}'

            series_metadata = {
                'title': series_info['original_name'],
                'sortTitle': normalize_title(series_info['original_name']),
                'year': series_info['first_air_date'][:4] if series_info['first_air_date'] else None,
                'tmdbId': tmdbid,
                'overview': series_info['overview'],
                'poster': images_url.format(series_info['poster_path']) if series_info['poster_path'] else None,
                'fanart': images_url.format(series_info['backdrop_path'])if series_info['backdrop_path'] else None,
                'alternateTitles': [x['title'] for x in alternative_titles['results']],
                'imdbId': external_ids['imdb_id']
            }

        return series_metadata


def normalize_title(title):
    WordDelimiterRegex = re.compile(r"(\s|\.|,|_|-|=|\|)+")
    PunctuationRegex = re.compile(r"[^\w\s]")
    CommonWordRegex = re.compile(r"\b(a|an|the|and|or|of)\b\s?")
    DuplicateSpacesRegex = re.compile(r"\s{2,}")

    title = title.lower()

    title = re.sub(WordDelimiterRegex, " ", title)
    title = re.sub(PunctuationRegex, "", title)
    title = re.sub(CommonWordRegex, "", title)
    title = re.sub(DuplicateSpacesRegex, " ", title)

    return title.strip()


def index_all_series():
    directories_metadata = []

    root_dir_ids = TableShowsRootfolder.select(TableShowsRootfolder.id).dicts()
    for root_dir_id in root_dir_ids:
        root_dir_subdirectories = list_series_directories(root_dir_id['id'])
        for root_dir_subdirectory in root_dir_subdirectories:
            root_dir_match = get_series_match(root_dir_subdirectory['directory'])
            if root_dir_match:
                directories_metadata.append(get_series_metadata(root_dir_match[0]['tmdbId']))

    return dumps(directories_metadata)


print(index_all_series())
