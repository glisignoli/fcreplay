#!/usr/bin/env python3
from fcreplay.database import Database
from fcreplay.getreplay import Getreplay
import docker
import os
import requests
import schedule
import shutil
import time
import uuid


class Tasker:
    def __init__(self):
        self.started_instances = {}
        self.db = Database()
        self.max_instances = 1
        self.max_fails = 5

    def check_for_replay(self) -> bool:
        if self.number_of_instances() >= self.max_instances:
            print(f"Maximum number of instances ({self.max_instances}) reached")
            return False

        print("Looking for replay")
        player_replay = self.db.get_oldest_player_replay()
        if player_replay is not None:
            print("Found player replay")
            self.launch_fcreplay()
            return True

        replay = self.db.get_oldest_replay()
        if replay is not None:
            print("Found replay")
            self.launch_fcreplay()
            return True

        print("No replays")
        return False

    def number_of_instances(self) -> int:
        d_client = docker.from_env()
        containers = d_client.containers.list()

        instance_count = 0
        for container in containers:
            if 'fcreplay-instance-' in container.name:
                instance_count += 1

        return instance_count

    def running_instance(self, instance_hostname) -> bool:
        try:
            d_client = docker.from_env()
            for i in d_client.containers.list():
                if instance_hostname in i.attrs['Config']['Hostname']:
                    return True
        except requests.exceptions.HTTPError:
            print(f"Failed to find container {instance_hostname}")
            return False

        return False

    def remove_temp_dirs(self):
        """Remove temp directories for containers no longer running."""
        remove_instances = []

        for docker_hostname in self.started_instances:
            if not self.running_instance(docker_hostname):
                print(f"Removing '/avi_storage_temp/{self.started_instances[docker_hostname]}'")
                shutil.rmtree(f"/avi_storage_temp/{self.started_instances[docker_hostname]}")
                remove_instances.append(docker_hostname)

        for i in remove_instances:
            del self.started_instances[i]

    def retry_failed_videos(self):
        """Retry failed videos."""
        print('Setting failed videos to retry')
        failed_replays = self.db.get_all_failed_replays(limit=1000)

        for r in failed_replays:
            if r.fail_count < self.max_fails:
                self.db.rerecord_replay(r.id)
                print(f"Marked failed replay {r.id} to be re-encoded")

    def delete_failed_videos(self):
        """Delete replays that have failed 5 times to record
        """
        failed_replays = self.db.get_all_failed_replays(limit=1000)
        for r in failed_replays:
            if r.fail_count >= self.max_fails:
                self.db.delete_replay(r.id)

    def launch_fcreplay(self):
        print("Getting docker env")
        d_client = docker.from_env()

        instance_uuid = str(uuid.uuid4().hex)

        if 'FCREPLAY_NETWORK' not in os.environ:
            os.environ['FCREPLAY_NETWORK'] = 'bridge'

        # Get fcreplay network list
        networks = os.environ['FCREPLAY_NETWORK'].split(',')

        print(f"Starting new instance with temp dir: '{os.environ['AVI_TEMP_DIR']}/{instance_uuid}'")
        c_instance = d_client.containers.run(
            'fcreplay/image:latest',
            command='fcrecord',
            cpu_count=int(os.environ['CPUS']),
            detach=True,
            mem_limit=str(os.environ['MEMORY']),
            network=networks[0],
            remove=True,
            name=f"fcreplay-instance-{instance_uuid}",
            volumes={
                str(os.environ['CLIENT_SECRETS']): {'bind': '/root/.client_secrets.json', 'mode': 'ro'},
                str(os.environ['CONFIG']): {'bind': '/root/config.json', 'mode': 'ro'},
                str(os.environ['DESCRIPTION_APPEND']): {'bind': '/root/description_append.txt', 'mode': 'ro'},
                str(os.environ['IA']): {'bind': '/root/.ia', 'mode': 'ro'},
                str(os.environ['ROMS']): {'bind': '/Fightcade/emulator/fbneo/ROMs', 'mode': 'ro'},
                str(os.environ['YOUTUBE_UPLOAD_CREDENTIALS']): {'bind': '/root/.youtube-upload-credentials.json', 'mode': 'ro'},
                f"{os.environ['AVI_TEMP_DIR']}/{instance_uuid}": {'bind': '/Fightcade/emulator/fbneo/avi', 'mode': 'rw'},
                str(os.environ['BAD_WORDS_FILE']): {'bind': '/root/bad_words.txt', 'mode': 'ro'}
            }
        )

        if len(networks) > 1:
            for n in networks[1:]:
                print(f"Adding container to network {n}")
                d_net = d_client.networks.get(n)
                d_net.connect(c_instance)

        print("Getting instance uuid")
        self.started_instances[c_instance.attrs['Config']['Hostname']] = instance_uuid

    def check_for_docker_network(self):
        d_client = docker.from_env()
        d_net = d_client.networks.list()
        networks = os.environ['FCREPLAY_NETWORK'].split(',')

        if set(networks) <= set([i.name for i in d_net]) is False:
            print(f"The folling networks don't exist: {set(networks) - set([i.name for i in d_net])}")
            return False

        return True

    def update_video_status(self):
        """Update the status for videos uploaded to archive.org
        """
        print("Checking status for completed videos")

        # Get all replays that are completed, where video_processed is false
        to_check = self.db.get_unprocessed_replays()

        for replay in to_check:
            # Check if replay has embeded video link. Easy way to do this is to check
            # if a thumbnail is created
            print(f"Checking: {replay.id}")
            if replay.video_youtube_uploaded:
                print(f"Checking url: http://img.youtube.com/vi/{replay.video_youtube_id}/0.jpg")
                try:
                    r = requests.get(f"http://img.youtube.com/vi/{replay.video_youtube_id}/0.jpg")
                except Exception as e:
                    print(f"Caught exception: {e}, when checking {replay.id}")
                    continue
            else:
                print(f"Checking url: https://archive.org/download/{replay.id.replace('@', '-')}/__ia_thumb.jpg")
                try:
                    r = requests.get(f"https://archive.org/download/{replay.id.replace('@', '-')}/__ia_thumb.jpg")
                except Exception as e:
                    print(f"Caught exception: {e}, when checking {replay.id}")
                    continue

            print(f"ID: {replay.id}, Status: {r.status_code}")
            if r.status_code == 200:
                self.db.set_replay_processed(challenge_id=replay.id)

    def recorder(self, max_instances=1):
        if self.check_for_docker_network() is False:
            return False

        schedule.every(10).to(30).seconds.do(self.remove_temp_dirs)
        schedule.every(30).to(60).seconds.do(self.check_for_replay)

        self.max_instances = max_instances

        if 'MAX_INSTANCES' in os.environ:
            self.max_instances = int(os.environ['MAX_INSTANCES'])

        self.check_for_replay()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def check_top_weekly(self):
        if 'GET_WEEKLY' in os.environ:
            if os.environ['GET_WEEKLY'].lower() == 'true':
                print("Getting weekly replays")
                g = Getreplay()
                schedule.every(1).hour.do(g.get_top_weekly)

                g.get_top_weekly()
                while True:
                    schedule.run_pending()
                    time.sleep(1)
            else:
                print("Not getting weekly replays")
        else:
            print("GET_WEEKLY is not set, not getting weekly replays")

    def check_video_status(self):
        self.update_video_status()
        schedule.every(1).hour.do(self.update_video_status)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def schedule_retry_failed_replays(self):
        self.retry_failed_videos()
        schedule.every(1).hour.do(self.retry_failed_videos)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def schedule_delete_failed_replays(self):
        self.delete_failed_videos()
        schedule.every(1).hour.do(self.delete_failed_videos)
        while True:
            schedule.run_pending()
            time.sleep(1)
