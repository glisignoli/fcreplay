from fcreplay.config import Config
from fcreplay.models import Base
from fcreplay.models import Job, Replays, Character_detect, Descriptions, Youtube_day_log
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import datetime
import logging

log = logging.getLogger('fcreplay')


class Database:
    """Database class to manage queries."""

    def __init__(self):
        """Initalise the database class.

        Raises:
            e: Raises an exception on error
        """
        config = Config()

        if 'DEBUG' in config.loglevel:
            sql_echo = True
        else:
            logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
            sql_echo = False

        """Create Engine"""
        try:
            log.debug(f"Creating DB Instance with: {config.sql_baseurl}")
            self.engine = create_engine(config.sql_baseurl, echo=sql_echo, pool_pre_ping=True)
            Base.metadata.create_all(self.engine)
        except Exception as e:
            log.error(f"Unable to connect to {config.sql_baseurl}: {e}")
            raise e

        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def add_replay(self, challenge_id,
                   p1_loc, p2_loc,
                   p1_rank, p2_rank,
                   p1, p2,
                   date_replay, length, created, failed, status, date_added,
                   player_requested, game, emulator, video_processed,
                   ia_filename="EMPTY",
                   fail_count=0
                   ):
        """Add a new replay to the database to be encoded.

        Args:
            challenge_id (str): fightcade challenge id
            p1_loc (str): Location of P1
            p2_loc (str): Location of P2
            p1_rank (str): Rank of P1 ('0', '1', '2', '3')
            p2_rank (str): Rank of P2 ('0', '1', '2', '3')
            p1 (str): P1 name
            p2 (str): P2 name
            date_replay (datetime): Date of replay
            length (float): Length of replay
            created (bool): If the replay is already created (usually False)
            failed (bool): If the replay is failed (usually False)
            status (str): Current status of the replay (usually ADDED)
            date_added (datetime): Data the replay was added
            player_requested (bool): Was the replay player requested
            game (str): Game name
            emulator (str): Emulator used
            video_processed (bool): Has the video been prossed (usually False)
            ia_filename (str, optional): Archive.org filename. Defaults to "EMPTY"
            fail_count (int, optional): Number of times the replay has failed. Defaults to 0

        """
        
        self.session.add(
            Replays(
                id=challenge_id,
                p1_loc=p1_loc,
                p2_loc=p2_loc,
                p1_rank=p1_rank,
                p2_rank=p2_rank,
                p1=p1,
                p2=p2,
                date_replay=date_replay,
                length=length,
                created=created,
                failed=failed,
                status=status,
                date_added=date_added,
                player_requested=player_requested,
                game=game,
                emulator=emulator,
                video_processed=video_processed,
                ia_filename=ia_filename,
                fail_count=fail_count
            )
        )
        self.session.commit()
        # self.session.close()

    def add_ia_filename(self, challenge_id, filename):
        """Add an IA filename to the database.

        Args:
            challenge_id (str): Challenge id
            filename (str): Filename
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id,
        ).update(
            {'ia_filename': filename}
        )
        self.session.commit()
        # self.session.close()

    def get_single_replay(self, challenge_id):
        """Get a single replay by id.

        Args:
            challenge_id (str): Challenge id
        """
        
        replay = self.session.query(Replays).filter_by(
            id=challenge_id
        ).first()
        # self.session.close()

        return(replay)

    def update_player_requested(self, challenge_id):
        """Update whether replay is player requested.

        Args:
            challenge_id (str): Challenge id
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id,
        ).update(
            {'player_requested': True}
        )
        self.session.commit()
        # self.session.close()

    def add_detected_characters(self, challenge_id, p1_char, p2_char, vid_time, game):
        """Add detected characters to the replay.

        Args:
            challenge_id (str): Challenge id of the replay
            p1_char (str): P1 character
            p2_char (str): P2 character
            vid_time (str): Time in the video the character was detected
            game (str): Game name
        """
        
        self.session.add(Character_detect(
            challenge_id=challenge_id,
            p1_char=p1_char,
            p2_char=p2_char,
            vid_time=vid_time,
            game=game
        ))
        self.session.commit()
        # self.session.close()

    def add_job(self, challenge_id, start_time, length):
        """Add a new encoding job to the database.

        Args:
            challenge_id (str): Challenge id
            start_time (datetime): Time replay was added to be encoded
            length (str): Length of the replay
        """
        
        self.session.add(Job(
            id=challenge_id,
            start_time=start_time,
            instance=length
        ))
        self.session.commit()
        # self.session.close()

    def remove_job(self, challenge_id):
        """Remove a job from the database.

        Args:
            challenge_id (str): Challenge id
        """
        
        self.session.query(Job).filter_by(
            id=challenge_id
        ).delete()
        self.session.commit()
        # self.session.close()

    def get_job(self, challenge_id):
        """Return a job by its id

        Args:
            challenge_id (str): Challenge id

        Returns:
            sqlalchemy.object: Returns sqlalchemy object of job
        """
        
        job = self.session.query(
            Job
        ).filter_by(
            id=challenge_id
        ).first()
        # self.session.close()
        return job

    def get_job_count(self):
        """Return the number of jobs in the database.

        Returns:
            str: Number of jobs
        """
        
        count = self.session.execute('select count(id) from job').first()[0]
        # self.session.close()
        return count

    def get_all_count(self):
        """Return the total number of replays in the database.

        Returns:
            str: Number of replays
        """
        
        count = self.session.execute('select count(id) from replays').first()[0]
        # self.session.close()
        return count

    def get_failed_count(self):
        """Return the number of failed replays.

        Returns:
            str: Number of failed replays.
        """
        
        count = self.session.execute('select count(id) from replays where failed = true').first()[0]
        # self.session.close()
        return count

    def get_broken_count(self):
        """Return the number of 'broken' replays

        Returns:
            str: Number of broken replays
        """
        
        count = self.session.execute("select count(id) from replays where status not like 'ADDED' and status not like 'FINISHED' and failed is false").first()[0]
        # self.session.close()
        return count

    def get_pending_count(self):
        """Get the number of pending replays.

        Returns:
            str: Number of pending replays
        """
        
        count = self.session.execute("select count(id) from replays where created = false and failed = false").first()[0]
        # self.session.close()
        return count

    def get_finished_count(self):
        """Get the number of completed replays.

        Returns:
            str: Number of completed replays
        """
        
        count = self.session.execute("select count(id) from replays where created = true and failed = false").first()[0]
        # self.session.close()
        return count

    def update_status(self, challenge_id, status):
        """Update the status of a replay.

        Args:
            challenge_id (str): Challenge id
            status (str): Status
        """

        ## TODO Add method to verify status code
        
        self.session.query(Replays).filter_by(
            id=challenge_id,
        ).update(
            {'status': status}
        )
        self.session.commit()
        # self.session.close()

    def add_description(self, challenge_id, description):
        """Add a description to the database.

        Args:
            challenge_id (str): Challenge id
            description (str): Description
        """
        
        self.session.add(Descriptions(
            id=challenge_id,
            description=description
        ))
        self.session.commit()
        # self.session.close()

    def update_youtube_day_log_count(self, count, date):
        """update youtube day log.

        Args:
            count (int): Number of replays uploaded to youtube
            date (datetime): Current date
        """
        
        self.session.query(Youtube_day_log).filter_by(
            id='count'
        ).update(
            {
                'count': count,
                'date': date
            }
        )
        self.session.commit()
        # self.session.close()

    def get_youtube_day_log(self):
        """Get youtube day log.

        Returns:
            sqlalchemy.object: Contains the date and count
        """
        
        day_log = self.session.query(
            Youtube_day_log
        ).filter_by(
            id='count'
        ).first()
        # self.session.close()

        return day_log

    def get_oldest_player_replay(self):
        """Get the oldest player that is waiting to be encoded.

        Returns:
            sqlalchemy.object: Contains the replay as a sqlalchemy.object
        """
        
        replay = self.session.query(
            Replays
        ).filter_by(
            player_requested=True,
            created=False,
            failed=False,
            status='ADDED'
        ).order_by(
            Replays.date_added.desc()
        ).first()
        # self.session.close()
        return replay

    def get_random_replay(self):
        """Get a random replay.

        Returns:
            sqlalchemy.object: Contains the replay as a sqlalchemy.object
        """
        
        replay = self.session.query(
            Replays
        ).filter_by(
            failed=False,
            created=False,
            status='ADDED'
        ).order_by(
            func.random()
        ).first()
        # self.session.close()

        return replay

    def get_oldest_replay(self):
        """Get the oldest replay waiting to be encoded.

        Returns:
            sqlalchemy.object: Contains the replay as a sqlalchemy.object
        """
        
        replay = self.session.query(
            Replays
        ).filter_by(
            failed=False,
            created=False,
            status='ADDED'
        ).order_by(
            Replays.date_added.desc()
        ).first()
        # self.session.close()

        return replay

    def update_failed_replay(self, challenge_id):
        """Increments the failed replay count for a replay

        Args:
            challenge_id (str): Challenge id
        """
        
        failed_replay = self.session.query(Replays).filter_by(
            id=challenge_id
        ).first()
        if not isinstance(failed_replay.fail_count, int):
            n = 1
        else:
            n = failed_replay.fail_count + 1

        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {
                'failed': True,
                'fail_count': n
            }
        )
        self.session.commit()
        # self.session.close()

    def update_created_replay(self, challenge_id):
        """Marks the replay as created

        Args:
            challenge_id (str): Challenge id
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {
                'created': True
            }
        )
        self.session.commit()
        # self.session.close()


    def get_unprocessed_replays(self):
        """Get all replays that are unprocessed.

        Returns:
            sqlalchemy.object: Returns a sqlalchemy.object containing all unprocessed replays
        """
        
        replays = self.session.query(
            Replays
        ).filter_by(
            failed=False,
            created=True,
            video_processed=False
        ).all()
        # self.session.close()
        return replays

    def set_replay_processed(self, challenge_id):
        """Set the replay as processed.

        Args:
            challenge_id (str): Challenge id
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {'video_processed': True, "date_added": datetime.datetime.now()}
        )
        self.session.commit()
        # self.session.close()

    def set_youtube_uploaded(self, challenge_id, yt_bool):
        """Set whether or not video has been uploaded to youtube.

        Args:
            challenge_id (str): Challenge id
            yt_bool (bool): Has the video been uploaded to youtube
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {'video_youtube_uploaded': yt_bool}
        )
        self.session.commit()
        # self.session.close()

    def set_youtube_id(self, challenge_id, yt_id):
        """Set the youtube_id of a challenge.

        Args:
            challenge_id (str): Challenge id
            yt_id (str): Youtube id of the replay
        """
        
        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {'video_youtube_id': yt_id}
        )
        self.session.commit()
        # self.session.close()

    def rerecord_replay(self, challenge_id):
        """Rerecords a replay of a given challenge .

        Args:
            challenge_id (str): Challenge id
        """
        
        # Set replay to original status
        self.session.query(Replays).filter_by(
            id=challenge_id
        ).update(
            {'failed': False, 'created': False, 'status': 'ADDED'}
        )
        self.session.commit()

        # Remove description if it exists
        self.session.query(Descriptions).filter_by(
            id=challenge_id
        ).delete()
        self.session.commit()

        # Remove job if it exists
        self.session.query(Job).filter_by(
            id=challenge_id
        ).delete()
        self.session.commit()

        # Remove character detection if it exists
        self.session.query(Character_detect).filter_by(
            challenge_id=challenge_id
        ).delete()
        self.session.commit()
        # self.session.close()

    def delete_replay(self, challenge_id):
        """Delete a replay.

        Args:
            challenge_id (str): Challenge id
        """
        
        # Remove replay if it exists
        self.session.query(Replays).filter_by(
            id=challenge_id,
        ).delete()
        self.session.commit()

        # Remove description if it exists
        self.session.query(Descriptions).filter_by(
            id=challenge_id
        ).delete()
        self.session.commit()

        # Remove job if it exists
        self.session.query(Job).filter_by(
            id=challenge_id
        ).delete()
        self.session.commit()

        # Remove character detection if it exists
        self.session.query(Character_detect).filter_by(
            challenge_id=challenge_id
        ).delete()
        self.session.commit()
        # self.session.close()

    def get_all_failed_replays(self, limit=10):
        """Get all failed replays.

        Args:
            limit (int, optional): Number of replays to return. Defaults to 10.

        Returns:
            sqlalchemy.object: sqlalchemy.object containing failed replays
        """
        
        failed_replays = self.session.query(Replays).filter_by(
            failed=True,
        ).limit(limit).all()
        # self.session.close()
        return failed_replays

    def get_all_finished_replays(self, limit=10, order_by=Replays.date_added.desc()) -> list[Replays]:
        """Get all the finished replays.

        Args:
            limit (int, optional): Number of replays to return. Defaults to 10.

        Returns:
            sqlalchemy.object: sqlalchemy.object containing finished replays
        """
        
        replays = self.session.query(Replays).filter_by(
            failed=False,
            created=True
        ).order_by(order_by).limit(limit).all()
        # self.session.close()
        return replays

    def get_all_queued_replays(self, limit=10):
        """Get all queued replays.

        Args:
            limit (int, optional): Number of replays to return. Defaults to 10.

        Returns:
            sqlalchemy.object: sqlalchemy.object containing queued replays.
        """
        
        replays = self.session.query(Replays).filter_by(
            failed=False,
            created=False
        ).limit(limit).all()
        # self.session.close()
        return replays

    def get_all_players(self, limit=10) -> list[str]:
        """Get all players.

        Args:
            limit (int, optional): Number of players to return. Defaults to 10.

        Returns:
            list: List of play names
        """
        
        replays = self.session.query(Replays).limit(limit).all()
        # self.session.close()

        players = set()

        for replay in replays:
            players.add(replay.p1)
            players.add(replay.p2)

        return list(players)

    def get_all_broken_replays(self, limit=10):
        """Get broken replays.

        Args:
            limit (int, optional): Number of replays to return. Defaults to 10.

        Returns:
            sqlalchemy.object: sqlalchemy.object containing broken replays.
        """
        
        replays = self.session.query(Replays).filter(
            Replays.failed == False,
            Replays.status != 'ADDED',
            Replays.status != 'FINISHED'
        ).limit(limit).all()
        # self.session.close()
        return replays

    def get_all_queued_player_replays(self):
        """Get all queued player plays .

        Returns:
            sqlalchemt.object: Returns a sqlalchemy.object containing queued replays
        """
        
        replays = self.session.query(
            Replays
        ).filter_by(
            player_requested=True,
            failed=False,
            created=False
        ).order_by(
            Replays.date_added.asc()
        ).all()
        # self.session.close()
        return replays

    def get_description(self, challenge_id):
        """Get description of a challenge.

        Args:
            challenge_id (str): Challenge id

        Returns:
            sqlalchemy.object: sqlalchemy.object containing description
        """
        
        description = self.session.query(Descriptions).filter_by(
            id=challenge_id
        ).first()
        # self.session.close()
        return description
