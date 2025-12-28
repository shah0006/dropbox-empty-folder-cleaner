from enum import Enum, auto
from providers.interface import FileResource

class SyncActionType(Enum):
    COPY_LEFT_TO_RIGHT = auto()
    COPY_RIGHT_TO_LEFT = auto()
    DELETE_LEFT = auto()
    DELETE_RIGHT = auto()
    CONFLICT = auto()
    SKIP = auto()

class SyncAction:
    def __init__(self, action_type: SyncActionType, file: FileResource, reason: str):
        self.action_type = action_type
        self.file = file
        self.reason = reason
