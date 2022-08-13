#!/usr/bin/env python
import datetime
import i3ipc
import logging
import os
import subprocess
import threading
import time
import collections

from fcreplay.config import Config
from fcreplay.overlay_detection import OverlayDetection

if 'DISPLAY' in os.environ:
    import pyautogui

log = logging.getLogger('fcreplay')


class Record:
    def __init__(self):
        self.config = Config()
        self._last_good_frame_count = 0

    def _start_fcadefbneo(self, challenge_id: str, game_id: str):
        """Start fcadefbneo.

        Args:
            challenge_id (str): The challenge id
            game_id (str): The game id
        """
        log.info(f"/usr/bin/wine {self.config.fcadefbneo_path}/fcadefbneo.exe quark:stream,{game_id},{challenge_id}.2,7100 -q")
        running_env = os.environ.copy()
        running_env['WINEDLLOVERRIDES'] = "avifil32=n,b"
        subprocess.run(
            [
                '/usr/bin/wine',
                f'{self.config.fcadefbneo_path}/fcadefbneo.exe',
                f'quark:stream,{game_id},{challenge_id}.2,7100',
                'lua\\framecount.lua',
                '-q'
            ],
            env=running_env
        )

    def _cleanup_tasks(self):
        # Need to kill a bunch of processes and restart pulseaudio
        log.info("Killing fcadefbneo, wine, system32 and pulseaudio")
        subprocess.run(['pkill', '-9', 'fcadefbneo'])
        subprocess.run(['pkill', '-9', 'wine'])
        subprocess.run(['pkill', '-9', '-f', 'system32'])
        subprocess.run(['/usr/bin/pulseaudio', '-k'])
        log.info("Tasks killed")

    def find_record_dialog(self) -> bool:
        """Find the record dialog and return True if found.

        Returns:
            bool: True if the record dialog is found.
        """
        # Look for recording dialog
        i3 = i3ipc.Connection()
        root = i3.get_tree()
        for con in root:
            if isinstance(con.name, str):
                if 'Set video compression option' in con.name:
                    # Found dialog. Click on ok
                    mouse_x = con.rect.x + 300
                    mouse_y = con.rect.y + 10
                    pyautogui.moveTo(mouse_x, mouse_y)
                    time.sleep(0.1)
                    pyautogui.click()
                    return True
        return False

    def get_framecount(self, replay_length_seconds) -> int:
        """Get the number of frames rendered.

        Args:
            replay_length_seconds (int): Length of the replay in seconds
              This is used to calculate if we are 'close enough' to the
              end of the replay.

        Raises:
            TypeError: If a non-integer is found in the framecount
            ValueError: If a non-integer is found in the framecount

        Returns:
            int: The number of frames rendered
        """
        # Number of times to try and get the frame count
        retry = 5

        while retry >= 1:
            with open(f"{self.config.fcadefbneo_path}/lua/framecount.txt", 'r') as f:
                frame_count_str = f.readline().strip()

            try:
                frame_count = int(frame_count_str)
                break
            except (TypeError, ValueError) as e:
                # Sometimes, when a recording is finished a newline will be written to the
                # framecount file. In this case the number of frames recorded will be 'pretty close'
                # to length of the replay multiplyed by the framerate

                # If the last good frame count is within say, 10% of the length multiplied by then
                # framerate, then return the last good frame count
                if self._last_good_frame_count >= (replay_length_seconds * 60 * 0.9):
                    return self._last_good_frame_count

                # Otherwise, we probably have encoutered a read error where the file was being written
                # to at the same time we tried to read it. I'm not 100% sure about this. But it seems possible
                retry -= 1
                if retry <= 0:
                    # If we fail to get the frame count after 5 tries, then raise an error
                    log.error(f"Failed to get frame count, frame_count: {frame_count_str}")
                    raise e
                time.sleep(0.1)
                continue
            except Exception as e:
                # This is to capture any other errrors that might occur
                log.exception(f"Unexpected error: {e}")

        self._last_good_frame_count = frame_count
        return frame_count

    def _start_pulseaudio(self):
        """Start pulseaudio."""
        log.info("Starting pulseaudio")
        subprocess.Popen(
            ['pulseaudio', '-v', '--exit-idle-time=-1'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def _start_ggpo_thread(self, challenge_id: str, game_id: str):
        """Start ggpo thread.

        Args:
            challenge_id (str): The challenge id
            game_id (str): The game id
        """
        log.info("Starting fcadefbneo thread")
        log.debug(f"Arguments: {self.config.fcadefbneo_path}, {challenge_id}, {game_id}")

        ggpo_thread = threading.Thread(
            target=self._start_fcadefbneo,
            args=[challenge_id, game_id])
        ggpo_thread.start()
        log.info("Started ggpofbneo")

    def check_if_replay_started(self, kill_time: int):
        """Check if the replay has started.

        Args:
            kill_time (int): Time to wait raising TimeoutError

        Raises:
            TimeoutError: Raised kill_time has been exceded

        Returns:
            bool: True if the replay has started
        """
        second_count = (datetime.datetime.now() - self.begin_time).seconds

        if os.path.exists(f"{self.config.fcadefbneo_path}/fightcade/started.inf"):
            log.info('First frame displayed. Looking for recording dialog')
            if self.find_record_dialog():
                return True

        # Timeout reached, exiting
        if second_count > kill_time:
            log.info('Match never started, exiting')
            self._cleanup_tasks()
            raise TimeoutError

        return False

    def main(self, challenge_id: str, replay_length_seconds: int, kill_time: int, game_id: str):
        """Main function.

        Args:
            challenge_id (str): The challenge id
            replay_length_seconds (int): Fightcade reported replay length in seconds
            kill_time (int): [description]. Defaults to None.
            game_id (str): The game id

        Raises:
            TimeoutError: Raised if the match has not started after kill_time seconds
              or if the time spent recording the match is longer than kill_time

        Returns:
            bool: Returns true if recording is finished
        """
        # Start pulseaduo
        self._start_pulseaudio()

        # Get start time
        self.begin_time = datetime.datetime.now()

        # Make sure 'started.inf' is missing
        if os.path.exists(f"{self.config.fcadefbneo_path}/fightcade/started.inf"):
            os.remove(f"{self.config.fcadefbneo_path}/fightcade/started.inf")

        # Start fightcade fbneo thread
        self._start_ggpo_thread(challenge_id=challenge_id, game_id=game_id)

        # Start overlay detection
        # This requires the 'fightcade' directory exists inside the fbneo directory
        # if it doesn't exists, then this will fail
        overlay_detection = OverlayDetection()
        overlay_detection.start()

        # Check to see if fcadefbneo has started playing
        log.info('Checking to see if replay has started')
        while True:
            try:
                if self.check_if_replay_started(kill_time):
                    break
            except TimeoutError:
                log.info('Match never started, exiting')
                self._cleanup_tasks()
                raise TimeoutError

        # Reset the begin time
        self.begin_time = datetime.datetime.now()
        minute_time = -1

        # Initalise the framecount. Do this by setting up a 'queue' with a
        # maximum length of 10. Then append each time to it. The 'last'
        # element of the queue is the current frame. If all the elements
        # of the queue are the same, then the rendering is finished
        frame_counts = collections.deque(maxlen=10)

        # Append two elements so that the queue isn't empty
        frame_counts.append(-1)
        frame_counts.append(0)

        while True:
            # Add the current running time to the queue
            frame_counts.append(self.get_framecount(replay_length_seconds))

            # Debug the framecount
            log.debug(f"Frame count is: {frame_counts[-1]}, or {int((frame_counts[-1] / 60) / 60)} of {(int(replay_length_seconds / 60))} minutes")

            # Only display the minute time every minute, and never display 0 minutes
            if int(frame_counts[-1] / 60 / 60) != minute_time:
                # Log the minute
                log.info(f'Minute: {int((frame_counts[-1] / 60) / 60)} of {(int(replay_length_seconds / 60))}')

            minute_time = int((frame_counts[-1] / 60) / 60)

            # Finished recording video if all elements of the queue are the same
            if len(set(frame_counts)) == 1:
                overlay_detection.stop()

                log.info("Stopping recording")

                # We need to manually stop the recording. Move the mouse into the
                # fcadefbneo window, press alt, then down*7, then enter/return.
                pyautogui.moveTo(700, 384)
                time.sleep(0.05)
                pyautogui.press('alt')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)
                pyautogui.keyDown('enter')
                time.sleep(0.05)
                pyautogui.keyUp('enter')

                # Sleep for 2 seconds here in case there is some sort of delay writing file
                time.sleep(2)
                self._cleanup_tasks()

                log.info("Recording stopped")
                return True

            # Kill Timeout reached
            if int(frame_counts[-1] / 60) > (replay_length_seconds + kill_time):
                log.error(f"Recording time was {frame_counts[-1] / 60} and went on longer than '{replay_length_seconds} + {kill_time}'")
                raise TimeoutError

            # So sleeping for 0.1 seconds doesn't work. The file only gets updated every 0.2 seconds or something
            time.sleep(0.2)
