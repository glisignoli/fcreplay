""" When updating these status codes, make sure to also update the websiteV
status codes as well
"""

from dataclasses import dataclass


@dataclass
class status:
    ADDED: str = "ADDED"
    FAILED: str = "FAILED"
    JOB_ADDED: str = "JOB_ADDED"
    REMOVED_JOB: str = "REMOVED_JOB"
    RECORDING: str = "RECORDING"
    RECORDED: str = "RECORDED"
    MOVED: str = "MOVED"
    BROKEN_CHECK: str = "BROKEN_CHECK"
    DESCRIPTION_CREATED: str = "DESCRIPTION_CREATED"
    THUMBNAIL_CREATED: str = "THUMBNAIL_CREATED"
    UPLOADING_TO_IA: str = "UPLOADING_TO_IA"
    UPLOADED_TO_IA: str = "UPLOADED_TO_IA"
    UPLOADING_TO_YOUTUBE: str = "UPLOADING_TO_YOUTUBE"
    UPLOADED_TO_YOUTUBE: str = "UPLOADED_TO_YOUTUBE"
    REMOVED_GENERATED_FILES: str = "REMOVED_GENERATED_FILES"
    FINISHED: str = "FINISHED"
    TOO_SHORT: str = "TOO_SHORT"
    ALREADY_EXISTS: str = "ALREADY_EXISTS"
    MARKED_PLAYER: str = "MARKED_PLAYER"
    UNSUPPORTED_GAME: str = "UNSUPPORTED_GAME"
    INVALID_URL: str = "INVALID_URL"
    REPLAY_NOT_FOUND: str = "REPLAY_NOT_FOUND"
    BAD_WORDS_CHECKED: str = "BAD_WORDS_CHECKED"
    BANNED_USER: str = "BANNED_USER"
