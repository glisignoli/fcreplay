# This is a SLOW long running test to check the functionality of the fcreplay.
# This requires docker and a bunch of disk space
import docker
import gzip
import json
import os
import pytest
import requests
import subprocess
import time
import yaml

from pylinkvalidator.api import crawl, crawl_with_options

@pytest.mark.slow
class TestFunctionality:
    def _standup(self) -> bool:
        """Stop postgres if it's running .

        Returns:
            bool: True
        """
        if self._is_container_running('postgres_container'):
            # Kill running postgres container
            print("Stopping postgres")
            subprocess.run(['docker-compose', 'stop', 'postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['docker-compose', 'rm', '-f', 'postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True

    def _check_docker_compose(self) -> bool:
        """Check to see if docker-compose is installed

        Returns:
            bool: True if docker-compose is installed
        """
        rc = subprocess.run(['docker-compose', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if rc.returncode != 0:
            print(f"Stdout: {str(rc.stdout)}\nStderr: {str(rc.stderr)}")
            raise Exception("Docker-compose is not installed")

        return True

    def _is_upload_enabled(self) -> bool:
        """Check to see if upload_to_ia and upload_to_yt are set in the config.

        Returns:
            bool: True if upload_to_ia and upload_to_yt are set
        """
        config = self._get_config()
        if config['upload_to_ia'] or config['upload_to_yt']:
            return True
        return False

    def _get_config(self) -> dict:
        """Get the current config file.

        Returns:
            dict: The config file
        """
        override_content = self._get_override('./docker-compose.override.yml')
        environment_vars = override_content['services']['fcreplay-tasker']['environment']

        for env_var in environment_vars:
            if 'CONFIG' in env_var.split('=')[0]:
                config_file = env_var.split('=')[1]

                with open(config_file) as f:
                    config_dict = json.load(f)

                return config_dict

        raise Exception('CONFIG environment variable not found in docker-compose.override.yml')

    def _get_override(self, override_file: str) -> dict:
        """Get the override file.

        Args:
            override_file (str): Name of the override file

        Returns:
            dict: Override file
        """
        with open(override_file) as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def _move_database(self, src: str, dest: str):
        """Move database from src to dest .

        Args:
            src (str): Source path
            dest (str): Destination path
        """
        # Check backup_path doesn't exist
        if os.path.exists(dest):
            return False

        # Backup the database
        rc = subprocess.run(['sudo', 'mv', src, dest])
        if rc.returncode != 0:
            raise Exception(f"Failed to move database from {src} to {dest}")

        # Fix new directory permissions
        rc = subprocess.run(['sudo', 'chmod', '0777', dest])

    def _is_container_running(self, container_name: str, fuzzy=False) -> bool:
        """Return True if container_name is running in the environment.

        Args:
            container_name (str): Name of the container to check
            fuzzy (bool, optional): If True, fuzzy match the container name. Defaults to False.

        Returns:
            bool: True if container is running
        """
        client = docker.from_env()
        containers = client.containers.list()
        for container in containers:
            if fuzzy:
                if container_name in container.name:
                    return True
            else:
                if container.name == container_name:
                    return container.status == 'running'

        return False

    def _start_postgres_container(self) -> bool:
        """Start postgres container.

        Returns:
            bool: True if container is running
        """
        # We can't just use docker-compose up because fcreplay-site will fail locally due to service ports not being available.
        # Start postgres container
        subprocess.run(['docker-compose', 'up', '-d', 'postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

        # Wait for postgres to start
        pg_count = 0
        while not self._is_container_running('postgres_container'):
            pg_count += 1
            time.sleep(1)

            if pg_count > 30:
                return False

        # Clear the database
        rc_status = self._drop_fcreplay_database()

        if not rc_status:
            return False

        # Create the database
        rc_status = self._create_fcreplay_database()

        if not rc_status:
            return False
        return True

    def _drop_fcreplay_database(self) -> bool:
        """Drop databases from container.

        Returns:
            bool: True if container is clean
        """
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'dropdb', '--if-exists', '-U', 'fcreplay', 'fcreplay'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if rc.returncode != 0:
            print(f"Stdout: {str(rc.stdout)}\nStderr: {str(rc.stderr)}")
            raise Exception("Failed to drop database")

        return True

    def _create_fcreplay_database(self) -> bool:
        """Create databases from container.

        Returns:
            bool: True if container is clean
        """
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'createdb', '-U', 'fcreplay', 'fcreplay'])

        if rc.returncode != 0:
            raise Exception("Failed to create database")

        return True

    def _check_video_status_empty(self) -> bool:
        """Check if video status is empty.

        Returns:
            bool: True if video status is empty
        """
        # Check the video status
        # Wait for fcreplay-tasker-check_video_status to start
        rc = subprocess.run(['docker-compose', 'up', '-d', 'fcreplay-tasker-check_video_status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-tasker-check_video_status_1'):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                raise Exception('fcreplay-tasker-check_video_status failed to start')

        # Wait for 10 seconds
        time.sleep(10)

        # Check the postgres database to see if some videos were added (should be none)
        print("Checking database")
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'psql', '-U', 'fcreplay', '-d' 'fcreplay', '-c', 'SELECT * FROM replays;'], stdout=subprocess.PIPE)

        # Kill the fcreplay-tasker-check_video_status container
        subprocess.run(['docker-compose', 'stop', 'fcreplay-tasker-check_video_status'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if "(0 rows)" in rc.stdout.decode('utf-8'):
            return True
        else:
            return False

    def _check_top_weekly(self) -> bool:
        """Check the top weekly videos.

        Returns:
            bool: True if top weekly videos are correct
        """
        # Wait for fcreplay-tasker-check_top_weekly to start
        rc = subprocess.run(['docker-compose', 'up', '-d', 'fcreplay-tasker-check_top_weekly'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-tasker-check_top_weekly_1'):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                print("Stdout: " + str(rc.stdout) + "\nStderr: " + str(rc.stderr))
                raise Exception('fcreplay-tasker-check_top_weekly failed to start')

        # Wait for 30 seconds
        print("Waiting for videos to be added to database")
        time.sleep(30)

        # Check the postgres database to see if some videos were added (should be 1 or more)
        print("Checking database")
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'psql', '-U', 'fcreplay', '-d' 'fcreplay', '-c', 'SELECT * FROM replays;'], stdout=subprocess.PIPE)

        # Kill the fcreplay-tasker-check_top_weekly container
        subprocess.run(['docker-compose', 'stop', 'fcreplay-tasker-check_top_weekly'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if "(0 rows)" in rc.stdout.decode('utf-8'):
            return False
        else:
            return True

    def _delete_replay(self, id='9999999999999-9999', del_extras=False) -> bool:
        """Delete a replay.

        Args:
            id (str, optional): ID of the replay to delete. Defaults to '9999999999999-9999'.
            del_extras (bool, optional): Delete the extra entries from other tables. Defaults to False.

        Returns:
            bool: True if replay was deleted
        """
        sql_query = f"DELETE FROM replays WHERE id = '{id}';"

        print("Deleting replay")
        self._run_sql(sql_query)

        if del_extras:
            print("Deleting extra entries")
            self._run_sql(f"DELETE FROM job WHERE id = '{id}';")
            self._run_sql(f"DELETE FROM descriptions WHERE id = '{id}';")
            self._run_sql(f"DELETE FROM character_detect WHERE challenge_id = '{id}';")

        return True

    def _add_replay(self, id='9999999999999-9999', status='ADDED', failures=0, add_extras=False) -> bool:
        """Add a replay.

        Args:
            id (str, optional): ID of the replay. Defaults to '9999999999999-9999'.
            status (str, optional): Status of the replay. Defaults to 'ADDED'.
            failures (int, optional): Number of failures. Defaults to 0.
            add_extras (bool, optional): Add entries to DB for description, job and character_detection. Defaults to False.

        Returns:
            bool: True if the broken replay was added
        """
        sql_query = f"INSERT INTO replays \
                (id, \
                p1_loc, p2_loc, \
                p1, p2, \
                date_replay, \
                length, \
                created, failed, \
                status, \
                date_added, \
                player_requested, game, emulator, \
                video_processed, p1_rank, p2_rank, video_youtube_uploaded, video_youtube_id, fail_count, ia_filename) \
            VALUES \
                ('{id}', \
                'NZ', 'NZ', \
                'Fake1', 'Fake2', \
                '2021-11-08 23:34:46', \
                '915', \
                FALSE, TRUE, \
                '{status}', \
                '2021-11-09 00:48:58.33171', \
                FALSE, 'ssf2xjr1', 'fbneo', \
                FALSE, 4, 5, NULL, NULL, {failures}, 'EMPTY');"

        print("Inserting replay into database")
        self._run_sql(sql_query)

        if add_extras:
            print("Inserting job entry into database")
            job_sql = f"INSERT INTO job (id, start_time, instance) VALUES ('{id}' , '2021-11-08 23:34:46', '123456abcdef');"
            self._run_sql(job_sql)

            print("Interting description entry into database")
            description_sql = f"INSERT INTO descriptions (id, description) VALUES ('{id}', 'FAKE DESCRIPTION');"
            self._run_sql(description_sql)

            character_detection_sql = f"INSERT INTO character_detect \
                    (id, challenge_id, p1_char,p2_char, vid_time, game) \
            VALUES \
                    ('1', '{id}', 'FakeChar1', 'FakeChar2', '0:00:09', 'ssf2xjr1');"
            self._run_sql(character_detection_sql)

        return True

    def _run_sql(self, query: str) -> str:
        """Run a SQL query.

        Args:
            query (str): SQL query

        Returns:
            bool: True if the query ran successfully
        """
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'psql', '-U', 'fcreplay', '-d' 'fcreplay', '-c', query], stdout=subprocess.PIPE)
        if 'ERROR' in rc.stdout.decode('utf-8'):
            raise Exception(f'Error running SQL query: {query}')

        return rc.stdout.decode('utf-8')

    def _fix_failed_replay(self) -> bool:
        """Fix the 'failed' replay .

        Returns:
            bool: True if the broken replay was fixed
        """
        # Wait for fcreplay-tasker-retry_failed_replays to start
        subprocess.run(['docker-compose', 'up', '-d', 'fcreplay-tasker-retry_failed_replays'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-tasker-retry_failed_replays_1'):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                raise Exception('fcreplay-tasker-retry_failed_replays failed to start')

        # Wait for 30 seconds
        print("Waiting for replay to be fixed")
        time.sleep(30)

        # Kill the fcreplay-tasker-check_top_weekly container
        subprocess.run(['docker-compose', 'stop', 'fcreplay-tasker-retry_failed_replays'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Check the postgres database to see if some videos were added (should be 1 or more)
        return_status = True
        print("Checking database")
        replay_out = self._run_sql("SELECT failed FROM replays WHERE id = '9999999999999-9999' and failed IS FALSE;")
        job_out = self._run_sql("SELECT id FROM job WHERE id = '9999999999999-9999'")
        description_out = self._run_sql("SELECT id FROM descriptions WHERE id = '9999999999999-9999'")
        character_detection_out = self._run_sql("SELECT id FROM character_detect WHERE challenge_id = '9999999999999-9999'")

        if "(1 row)" not in replay_out:
            return_status = False

        if "(0 rows)" not in job_out:
            return_status = False

        if "(0 rows)" not in description_out:
            return_status = False

        if "(0 rows)" not in character_detection_out:
            return_status = False

        return return_status

    def _delete_failed_replay(self) -> bool:
        """Delete the 'failed' replay.

        Returns:
            bool: True if the broken replay was deleted
        """
        # Wait for fcreplay-tasker-delete_failed_replays to start
        subprocess.run(['docker-compose', 'up', '-d', 'fcreplay-tasker-delete_failed_replays'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-tasker-delete_failed_replays_1'):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                raise Exception('fcreplay-tasker-delete_failed_replays failed to start')

        # Wait for 30 seconds
        print("Waiting for replay to be deleted")
        time.sleep(30)

        # Kill the fcreplay-tasker-check_top_weekly container
        subprocess.run(['docker-compose', 'stop', 'fcreplay-tasker-delete_failed_replays'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Check the postgres database to see if some videos were added (should be 1 or more)
        return_status = True
        print("Checking database")
        replay_out = self._run_sql("SELECT id FROM replays WHERE id = '9999999999999-9999';")
        job_out = self._run_sql("SELECT id FROM job WHERE id = '9999999999999-9999';")
        description_out = self._run_sql("SELECT id FROM descriptions WHERE id = '9999999999999-9999';")
        character_detection_out = self._run_sql("SELECT id FROM character_detect WHERE challenge_id = '9999999999999-9999';")

        if "(0 rows)" not in replay_out:
            return_status = False

        if "(0 rows)" not in job_out:
            return_status = False

        if "(0 rows)" not in description_out:
            return_status = False

        if "(0 rows)" not in character_detection_out:
            return_status = False

        return return_status

    def _remove_replays(self) -> bool:
        """Remove all replays from the database.

        This will also store the length of the shortest replay
        in self.shortest_replay_length.

        Returns:
            bool: True if the replays were removed
        """
        # Find the replay with the shortest length
        shortest_replay_out = self._run_sql("SELECT id, length FROM replays ORDER BY length ASC LIMIT 1;")
        shortest_replay_id = shortest_replay_out.split('\n')[2].split('|')[0].strip()

        # Get the length and store it for later
        self.shortest_replay_length = int(shortest_replay_out.split('\n')[2].split('|')[1].strip())

        self._run_sql(f"DELETE FROM replays WHERE NOT id = '{shortest_replay_id}';")
        self._run_sql("DELETE FROM job;")
        self._run_sql("DELETE FROM descriptions;")
        self._run_sql("DELETE FROM character_detect;")

        return True

    def _start_tasker(self) -> bool:
        """Start fcreplay-tasker and wait for it to loaunch a recording instance.

        Returns:
            bool: True if the tasker started
        """
        # Wait for fcreplay-tasker to start
        subprocess.run(['docker-compose', 'up', '-d', 'fcreplay-tasker'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print('Waiting on fcreplay_fcreplay-tasker-1 to start')

        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-tasker_1'):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                raise Exception('fcreplay-tasker failed to start')

        print("Tasker instance started")
        print("Waiting for fcreplay-instance to start")
        check_count = 0
        while not self._is_container_running('fcreplay-instance-', fuzzy=True):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                raise Exception('fcreplay-instance failed to start')

        # Kill tasker instance
        subprocess.run(['docker-compose', 'stop', 'fcreplay-tasker'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("fcreplay-instance started")
        return True

    def _get_container_id(self, container_name: str) -> list:
        """Get the container ID for a container.

        Args:
            container_name (str): The name of the container

        Returns:
            str: The container ID

        """
        container_id = subprocess.run(['docker', 'ps', '-a', '-q', '--filter', f'name={container_name}'], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
        return container_id.splitlines()

    def _wait_for_recording(self) -> bool:
        """Wait for recording to finish.

        Returns:
            bool: True if recording finished
        """
        print("Waiting for recording to finish")

        print("Trying to find fcreplay-instance id")
        instance_id = self._get_container_id('fcreplay-instance')[0]
        print(f"Found instance id: {instance_id}")

        p = subprocess.Popen(['docker', 'logs', '-f', instance_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in p.stdout:
            print(line.decode('utf-8').strip())

        return True

    def _load_sql_data(self) -> bool:
        """Load sql data for site testing.

        Returns:
            bool: True if sql data was loaded
        """
        # Remove all existing data
        self._drop_fcreplay_database()

        # Create the database
        self._create_fcreplay_database()

        # Get sqldata
        with gzip.open('files/sample-data.sql.gz') as f:
            sql_data = f.read().decode('utf-8')

        # Load the sql data
        print("Loading the sql data")
        rc = subprocess.run(['docker-compose', 'exec', '-T', 'postgres', 'psql', '-U', 'fcreplay', '-d', 'fcreplay'], stdout=subprocess.PIPE, input=sql_data.encode('utf-8'))
        print(rc.stdout.decode('utf-8'))

        return True

    def _start_fcreplay_site(self) -> bool:
        """Start the fcreplay-site container.

        Returns:
            bool: True if the site started
        """
        # Start the site
        rc = subprocess.run(['docker-compose', 'run', '-d', '--service-ports', 'fcreplay-site'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.site_instance_id = rc.stdout.decode('utf-8').strip()

        # Wait for the container to start
        check_count = 0
        while not self._is_container_running('fcreplay_fcreplay-site', fuzzy=True):
            check_count += 1
            time.sleep(1)

            if check_count > 30:
                return False

        # Perform a http lookup to check if the site is up
        check_count = 0
        site_up = False

        while not site_up and check_count < 30:
            check_count += 1
            time.sleep(1)

            response = requests.get('http://localhost/')
            if response.status_code == 200:
                site_up = True

        return True

    def _check_for_broken_links(self) -> bool:
        """Check the fcreplay-site for broken links.

        Returns:
            bool: True if the site is working
        """
        crawled_site = crawl_with_options(
            ['http://localhost/'],
            {
                'depth': 2
            }
        )

        print(f'Crawled {len(crawled_site.pages)} pages')

        # check crawled_site for errors
        if len(crawled_site.error_pages) > 0:
            print('Found broken links')
            for error in crawled_site.error_pages:
                print(error)
            return False

        return True

    def _teardown(self) -> bool:
        """Teardown the container .

        Returns:
            bool: True if the container was successfully torn down
        """
        # Stop docker-compose
        subprocess.run(['docker-compose', 'stop'])
        subprocess.run(['docker-compose', 'rm', '-f'])

        # Check if fcreplay-site is running and remove it
        site_id = self._get_container_id('fcreplay_fcreplay-site')
        for id in site_id:
            subprocess.run(['docker', 'kill', id])
            subprocess.run(['docker', 'rm', '-f', id])

        return True

    def test_functionality(self):
        """Test the functionality of the fcreplay."""
        print("Checking if docker-compose is installed")
        assert self._check_docker_compose(), "Docker-compose is not installed"

        # Checking if upload is set (we don't want it set)
        print("Checking if upload_to_ia or upload_to_yt is enabled")
        assert not self._is_upload_enabled(), "Upload is enabled, this is not allowed"

        # Standup
        print("Running Standup")
        assert self._standup(), 'Failed to standup'

        # Check the postgres container
        print("Running Postgres")
        assert self._start_postgres_container(), 'Failed to start postgres container'

        # Run the fcreplay-tasker-check_video_status container
        print("Running check_video_status")
        assert self._check_video_status_empty(), "Status shouldn't create any videos!"

        # Run the fcreplay-tasker-check_top_weekly container
        print("Running check_top_weekly")
        assert self._check_top_weekly(), "Top weekly videos should have been created!"

        # Add a 'failed' replay to the db and see if it gets fixed
        print("Running add_failed_replay")
        assert self._add_replay(status='DESCRIPTION_CREATED', failures=1, add_extras=True), "Failed to add failed replay"

        # Try and fix the failed replay
        print("Running fix_failed_replay")
        assert self._fix_failed_replay(), "Failed to fix failed replay"

        # Try and delete failed replays
        # Add a 'failed' replay to the db and see if it gets fixed
        print("Running add_failed_replay with multiple failures")
        assert self._delete_replay(), "Failed to delete existing replay"
        assert self._add_replay(status='DESCRIPTION_CREATED', failures=100, add_extras=True), "Failed to add failed replay with multiple failures"
        print("Running delete_failed_replays")
        assert self._delete_failed_replay(), "Failed to delete failed replays"

        # Remove all replays from DB except the shortest one
        print("Removing all replays from DB except the shortest one")
        assert self._remove_replays(), "Failed to remove replays"

        # Run the fcreplay-tasker and wait for it to start a recording instance
        print("Starting fcreplay-tasker")
        assert self._start_tasker(), "Failed to start fcreplay-tasker"

        # Wait for recording to finish
        print("Waiting for recording to finish")
        assert self._wait_for_recording(), "Failed to wait for recording"

        # Teardown
        print("Running teardown")
        assert self._teardown(), 'Failed to teardown'

    def test_site(self):
        print("Checking if docker-compose is installed")
        assert self._check_docker_compose(), "Docker-compose is not installed"

        print("Running Standup")
        assert self._standup(), 'Failed to standup'

        # Start database
        print("Running Postgres")
        assert self._start_postgres_container(), 'Failed to start postgres container'

        # Load some sql data for site testing
        print("Loading sql data")
        assert self._load_sql_data(), "Failed to load sql data"

        """Test the fcreplay-site."""
        # Start the fcreplay-site
        print("Starting fcreplay-site")
        assert self._start_fcreplay_site(), "Failed to start fcreplay-site"

        # Check for broken links
        print("Checking for broken links")
        assert self._check_for_broken_links(), "Failed to check fcreplay-site"

        # Teardown
        print("Running teardown")
        assert self._teardown(), 'Failed to teardown'
