class Status:
    def __init__(self):
        self.status_description = {
            "ADDED": "Replay added",
            "FAILED": "Replay failed to encode",
            "JOB_ADDED": "Job added",
            "REMOVED_JOB": "Removed job",
            "RECORDING": "Recording started",
            "RECORDED": "Finished recording. Not yet uploaded",
            "MOVED": "Moved File",
            "BROKEN_CHECK": "Checking for broken file",
            "DESCRIPTION_CREATED": "Replay description created",
            "THUMBNAIL_CREATED": "Thumbnail created",
            "UPLOADING_TO_IA": "Uploading to internet archive",
            "UPLOADED_TO_IA": "Finished uploading to internet archive",
            "UPLOADING_TO_YOUTUBE": "Uploading to youtube",
            "UPLOADED_TO_YOUTUBE": "Finished uploading to youtube",
            "REMOVED_GENERATED_FILES": "Removed generated file",
            "FINISHED": "Replay encoding finished and uploaded successfully",
            "TOO_SHORT": "Replay is too short to encode",
            "ALREADY_EXISTS": "Replay already exists within database",
            "MARKED_PLAYER": "Replay marked as a player submitted replay",
            "UNSUPPORTED_GAME": "Game is unsupported",
            "INVALID_URL": "URL is invalid",
            "REPLAY_NOT_FOUND": "Replay was not found in database",
            "BAD_WORDS_CHECKED": "Bad words checked",
            "BANNED_USER": "One or more of the users in the replay is banned"
        }
