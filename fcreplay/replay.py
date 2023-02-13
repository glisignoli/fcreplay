from fcreplay.config import Config
from fcreplay.database import Database
from fcreplay.record import Record
from fcreplay.status import status
from fcreplay.thumbnail import Thumbnail
from fcreplay.updatethumbnail import UpdateThumbnail
from fcreplay.character_detection import CharacterDetection
from fcreplay.upload_youtube import UploadYouTube
from fcreplay.models import Replays

from internetarchive import get_item
from retrying import retry

import datetime
import glob
import json
import logging
import os
import pkg_resources
import re
import subprocess
import time
import sys

log = logging.getLogger('fcreplay')


class Replay:
    """Class for FightCade replays."""

    def __init__(self):
        """Initaliser for Replay class."""
        self.config = Config()
        self.db = Database()
        self.replay = self.get_replay()
        self.description_text = ""
        self.detected_characters = []

        with open(pkg_resources.resource_filename('fcreplay', 'data/supported_games.json')) as f:
            self.supported_games = json.load(f)

        # On replay start create a status file in /tmp - Legacy?
        with open('/tmp/fcreplay_status', 'w') as f:
            f.write(f"{self.replay.id} STARTED")

    def handle_fail(self, e: Exception):
        """Handle failures."""
        log.exception(e)
        log.info(f"Setting {self.replay.id} to failed")
        self.db.update_failed_replay(challenge_id=self.replay.id)
        self.update_status(status.FAILED)

        # Hacky as hell, but ensures everything gets killed
        if self.config.kill_all:
            subprocess.run(['pkill', '-9', 'fcadefbneo'])
            subprocess.run(['pkill', '-9', 'wine'])
            subprocess.run(['pkill', '-9', '-f', 'system32'])
            subprocess.run(['/usr/bin/pulseaudio', '-k'])
            subprocess.run(['pkill', '-9', 'tail'])
            subprocess.run(['killall5'])
            subprocess.run(['pkill', '-9', 'sh'])
        time.sleep(5)
        with open('/tmp/fcreplay_failed', 'w') as f:
            f.write("FAILED")

        sys.exit(1)

    def get_replay(self) -> Replays:
        """Get a replay from the database."""
        log.info('Getting replay from database')
        if self.config.player_replay_first:
            replay = self.db.get_oldest_player_replay()
            if replay is not None:
                log.info('Found player replay to encode')
                return replay
            else:
                log.info('No more player replays')

        if self.config.random_replay:
            log.info('Getting random replay')
            replay = self.db.get_random_replay()
            return replay
        else:
            log.info('Getting oldest replay')
            replay = self.db.get_oldest_replay()

        return replay

    def get_characters(self):
        """Get characters (if they exist) from pickle file."""
        c = CharacterDetection()
        self.detected_characters = c.get_characters()

        for i in self.detected_characters:
            self.db.add_detected_characters(
                challenge_id=self.replay.id,
                p1_char=i[0],
                p2_char=i[1],
                vid_time=i[2],
                game=self.replay.game
            )

    def add_job(self):
        """Update jobs database table with the current replay."""
        start_time = datetime.datetime.utcnow()
        self.update_status(status.JOB_ADDED)
        self.db.add_job(
            challenge_id=self.replay.id,
            start_time=start_time,
            length=self.replay.length
        )

    def remove_job(self):
        """Remove job from database."""
        self.update_status(status.REMOVED_JOB)
        self.db.remove_job(challenge_id=self.replay.id)

    def update_status(self, status):
        """Update the replay status."""
        log.info(f"Set status to {status}")
        # This file is legacy?
        with open('/tmp/fcreplay_status', 'w') as f:
            f.write(f"{self.replay.id} {status}")
        self.db.update_status(
            challenge_id=self.replay.id,
            status=status
        )

    def record(self):
        """Start recording a replay."""
        log.info(
            f"Starting capture with {self.replay.id} and {self.replay.length}")
        time_min = int(self.replay.length / 60)
        log.info(f"Capture will take {time_min} minutes")

        self.update_status(status.RECORDING)

        # Star a recording store recording status
        log.debug(
            f"""Starting record.main with argumens:
            fc_challenge_id={self.replay.id},
            fc_time={self.replay.length},
            kill_time={self.config.record_timeout},
            fcadefbneo_path={self.config.fcadefbneo_path},
            game_name={self.replay.game}""")

        Record().main(
            challenge_id=self.replay.id,
            replay_length_seconds=self.replay.length,
            kill_time=self.config.record_timeout,
            game_id=self.replay.game
        )

        log.info("Capture finished")
        self.update_status(status.RECORDED)

        return True

    def sort_files(self, avi_files_list: list):
        """Sort files.

        This sorts the avi files FBNeo generates. FBneo generates files that
        have a hexadecimal suffix added to them (08, 09, 0A, 0B...).

        Args:
            avi_files_list (list): List of avi files to sort

        Returns:
            list: Returns a sorted list of avi files
        """
        log.info("Sorting files")

        if len(avi_files_list) > 1:
            avi_dict = {}
            for i in avi_files_list:
                m = re.search('(.*)_([0-9a-fA-F]+).avi', i)
                avi_dict[i] = int(m.group(2), 16)
            sorted_avi_files_list = []
            for i in sorted(avi_dict.items(), key=lambda x: x[1]):
                sorted_avi_files_list.append(i[0])
            avi_files = [f"{self.config.fcadefbneo_path}/avi/" + i for i in sorted_avi_files_list]
        else:
            avi_files = [
                f"{self.config.fcadefbneo_path}/avi/" + avi_files_list[0]]

        return avi_files

    def get_resolution(self, aspect_ratio: list, video_resolution: list) -> list:
        """Return the correct resoltion for memcoder.

        Args:
            aspect_ratio (list): Supplied aspect ratio as list, eg: [4, 3]
            video_resolution (list): Supplied video resolution as list, eg: [1280, 720]

        Returns:
            list: Returns list containing the encoding resultion for memcoder, eg: [960, 720, 1280, 720]
        """
        # Find resolution
        multiplier = aspect_ratio[0] / aspect_ratio[1]
        desired_resolution = []

        # If the resolution is horozontal, use a horizontal HD resolution, otherwise use a vertical
        # resolution video
        if aspect_ratio[0] >= aspect_ratio[1]:
            desired_resolution = [video_resolution[1] * multiplier, video_resolution[1]]

            # Super wide games need to be done differently, looking at you darius...
            if desired_resolution[0] > video_resolution[0]:
                desired_resolution = [video_resolution[0],
                                      video_resolution[0] / multiplier]

        else:
            # Swap the resolutions, make the video verticle
            video_resolution = [video_resolution[1], video_resolution[0]]
            desired_resolution = [video_resolution[0] * multiplier, video_resolution[1]]

        desired_resolution.append(video_resolution[0])
        desired_resolution.append(video_resolution[1])

        desired_resolution = [int(a) for a in desired_resolution]
        return desired_resolution

    def encode(self):
        """Encode avi files.

        Raises:
            e: subprocess.CalledProcessError
        """
        log.info("Encoding lossless file")

        avi_files_list_glob = glob.glob(
            f"{self.config.fcadefbneo_path}/avi/*.avi")
        avi_files_list = []

        for f in avi_files_list_glob:
            avi_files_list.append(os.path.basename(f))

        log.info(f"List of files is: {avi_files_list}")

        # Sort files
        avi_files = self.sort_files(avi_files_list)

        # Get the correct screen resolution settings
        resolution = self.config.resolution
        aspect_ratio = self.supported_games[self.replay.game]['aspect_ratio']
        dsize = '/'.join(str(x) for x in aspect_ratio)

        r = self.get_resolution(aspect_ratio, resolution)

        # I can't stress enough how much you should not try and mess with the encoding settings!
        # 1. ffmpeg will not handle files generated by fbneo
        # 2. The files that fbneo generates need to be transcoded before they are encoded to h264 (h265 doesn't work well with archive.org)
        mencoder_options = [
            '/opt/mplayer/bin/mencoder', '-oac', 'mp3lame', '-lameopts', 'vbr=3',
            '-ovc', 'x264', '-x264encopts', 'preset=slow:threads=auto',
            '-vf', f"flip,scale={r[0]}:{r[1]},dsize={dsize},expand={r[2]}:{r[3]}::::", '-sws', '4',
            *avi_files,
            '-of', 'lavf',
            '-o', f"{self.config.fcadefbneo_path}/avi/{self.replay.id}.mp4"
        ]

        log.info(f"Running mencoder with: {' '.join(mencoder_options)}")

        mencoder_rc = subprocess.run(
            mencoder_options,
            capture_output=True
        )

        try:
            mencoder_rc.check_returncode()
        except subprocess.CalledProcessError as e:
            log.error(
                f"Unable to process avi files. Return code: {e.returncode}, stdout: {mencoder_rc.stdout}, stderr: {mencoder_rc.stderr}")
            raise e

    def remove_old_avi_files(self):
        """Remove old avi files."""
        log.info('Removing old avi files')
        old_files = glob.glob(f"{self.config.fcadefbneo_path}/avi/*.avi")

        for f in old_files:
            log.info(f"Removing {f}")
            os.unlink(f)

    def get_rank_letter(self, rank: int) -> str:
        """Return the rank letter.

        Args:
            rank (int): Rank number

        Returns:
            str: Rank letter
        """
        ranks = {
            '0': '?',
            '1': 'E',
            '2': 'D',
            '3': 'C',
            '4': 'B',
            '5': 'A',
            '6': 'S',
        }

        return ranks[str(rank)]

    def set_description(self):
        """Set the description of the video.

        Returns:
            boolean: Success or failure
        """
        log.info("Creating description")
        ranks = [
            self.get_rank_letter(self.replay.p1_rank),
            self.get_rank_letter(self.replay.p2_rank)
        ]
        tags = []

        if len(self.detected_characters) > 0:
            self.description_text = f"({self.replay.p1_loc}) {self.replay.p1} (Rank {ranks[0]}) vs "\
                f"({self.replay.p2_loc}) {self.replay.p2} {ranks[1]} - {self.replay.date_replay} "\
                f"\nFightcade replay id: {self.replay.id}"

            first_chapter = True
            for match in self.detected_characters:
                # Add characters to tags
                tags.append(match[1])
                tags.append(match[2])

                # Remove leading 0: from replays
                detect_time = re.sub('^0:', '', match[2])
                if first_chapter:
                    self.description_text += f"\n0:00 {match[0]} vs {match[1]}"
                    first_chapter = False
                else:
                    self.description_text += f"\n{detect_time} {match[0]} vs {match[1]}"

        else:
            self.description_text = f"({self.replay.p1_loc}) {self.replay.p1} vs " \
                                    f"({self.replay.p2_loc}) {self.replay.p2} - {self.replay.date_replay}" \
                                    f"\nFightcade replay id: {self.replay.id}"

        # Add tags to the description text
        tags.append(self.replay.p1)
        tags.append(self.replay.p2)

        self.description_text += f"\n#fightcade\n#{self.replay.game}\n#" + '\n#'.join(
            set(tags)).replace(' ', '')

        # Read the append file:
        if self.config.description_append_file[0] is True:
            # Check if file exists:
            if not os.path.exists(self.config.description_append_file[1]):
                log.error(
                    f"Description append file {self.config.description_append_file[1]} doesn't exist")
                return False
            else:
                with open(self.config.description_append_file[1], 'r') as description_append:
                    self.description_text += "\n" + description_append.read()

        self.update_status(status.DESCRIPTION_CREATED)
        log.info("Finished creating description")

        # Add description to database
        log.info('Adding description to database')
        self.db.add_description(
            challenge_id=self.replay.id, description=self.description_text)

        log.debug(
            f"Description Text is: {self.description_text.encode('unicode-escape')}")
        return True

    def check_bad_words(self):
        """Check if the description contains bad words.

        Returns:
            boolean: Success or failure
        """
        log.info("Checking bad words")
        try:
            with open(self.config.bad_words_file, 'r') as bad_words_file:
                bad_words = bad_words_file.read().splitlines()
        except FileNotFoundError:
            log.error(f"Bad words file {self.config.bad_words_file} doesn't exist")
            return False
        bad_words = [x.lower() for x in bad_words]

        for word in bad_words:
            for player in [self.replay.p1, self.replay.p2]:
                if word in player.lower():
                    log.error(f"Bad word: {word} detected in player: {player}")
                    self.update_status(status.BAD_WORDS_CHECKED)
                    log.info("Finished checking bad words")
                    return False

        self.update_status(status.BAD_WORDS_CHECKED)
        log.info("Finished checking bad words")
        return True

    def create_thumbnail(self):
        """Create thumbnail from video."""
        log.info("Making thumbnail")

        self.thumbnail = Thumbnail().get_thumbnail(self.replay)

        self.update_status(status.THUMBNAIL_CREATED)
        log.info("Finished making thumbnail")

    def update_thumbnail(self):
        """Add text, country and ranks to thumbnail."""
        log.info("Updating thumbnail")

        UpdateThumbnail().update_thumbnail(self.replay, self.thumbnail)

    @retry(wait_random_min=30000, wait_random_max=60000, stop_max_attempt_number=3)
    def upload_to_ia(self):
        """Upload to internet archive.

        Sometimes it will return a 403, even though the file doesn't already
        exist. So we decorate the function with the @retry decorator to try
        again in a little bit. Max of 3 tries
        """
        self.update_status(status.UPLOADING_TO_IA)
        title = f"{self.supported_games[self.replay.game]['game_name']}: ({self.replay.p1_loc}) {self.replay.p1} vs" \
                f"({self.replay.p2_loc}) {self.replay.p2} - {self.replay.date_replay}"
        filename = f"{self.replay.id}.mp4"
        date_short = str(self.replay.date_replay)[10]

        # Make identifier for Archive.org
        ident = str(self.replay.id).replace("@", "-")
        fc_video = get_item(ident)

        metadata = {
            'title': title,
            'mediatype': self.config.ia_settings['mediatype'],
            'collection': self.config.ia_settings['collection'],
            'date': date_short,
            'description': self.description_text,
            'subject': self.config.ia_settings['subject'],
            'creator': self.config.ia_settings['creator'],
            'language': self.config.ia_settings['language'],
            'licenseurl': self.config.ia_settings['license_url']}

        log.info("Starting upload to archive.org")
        fc_video.upload(f"{self.config.fcadefbneo_path}/avi/{filename}",
                        metadata=metadata, verbose=True)

        self.db.add_ia_filename(str(self.replay.id), filename)

        self.update_status(status.UPLOADED_TO_IA)
        log.info("Finished upload to archive.org")

    def upload_to_yt(self):
        """Upload video to youtube."""
        self.update_status(status.UPLOADING_TO_YOUTUBE)

        ranks = [
            self.get_rank_letter(self.replay.p1_rank),
            self.get_rank_letter(self.replay.p2_rank)
        ]

        title = f"{self.supported_games[self.replay.game]['game_name']}: {self.replay.p1} ({self.replay.p1_loc}, Rank {ranks[0]})  vs "\
                f"{self.replay.p2} ({self.replay.p2_loc}, Rank {ranks[1]})"
        filename = f"{self.replay.id}.mp4"
        import_format = '%Y-%m-%d %H:%M:%S'
        date_raw = datetime.datetime.strptime(
            str(self.replay.date_replay), import_format)

        # Trim title length
        if len(title) > 100:
            title = title[:99]
        log.info(f"Title is: {title}")

        # Trim playlist name length
        if len(self.supported_games[self.replay.game]['game_name']) > 100:
            playlist_name = self.supported_games[self.replay.game]['game_name'][:99]
        else:
            playlist_name = self.supported_games[self.replay.game]['game_name']

        # YYYY-MM-DDThh:mm:ss.sZ
        recording_date = date_raw.strftime('%Y-%m-%dT%H:%M:%S.0Z')

        # Do upload
        log.info("Uploading to youtube")
        try:
            upload = UploadYouTube(title=title,
                                   description=self.description_text,
                                   tags=None,
                                   video_path=f"{self.config.fcadefbneo_path}/avi/{filename}",
                                   playlist=playlist_name,
                                   thumbnail=self.thumbnail,
                                   recording_date=recording_date,
                                   player_requested=self.replay.player_requested
                                   )
            youtube_id = upload.upload()
        except Exception as e:
            log.error(f"Error uploading to youtube: {e}")
            return False

        log.info(f"Youtube id: {youtube_id}")

        if type(youtube_id) is bool or len(youtube_id) < 4:
            log.info('Unable to upload to youtube')
            self.db.set_youtube_uploaded(self.replay.id, False)
        else:
            self.db.set_youtube_uploaded(self.replay.id, True)
            self.db.set_youtube_id(self.replay.id, youtube_id)

        self.update_status(status.UPLOADED_TO_YOUTUBE)
        log.info('Finished uploading to Youtube')

    def set_created(self):
        """Update the video status to created."""
        self.update_status(status.FINISHED)
        self.db.update_created_replay(challenge_id=self.replay.id)
