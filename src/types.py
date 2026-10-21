from enum import Enum

class NSFWOption(Enum):
    SHOW_EVERYTHING = "Show everything"
    ONLY_NSFW = "Only NSFW"
    BLOCK_NSFW = "Block NSFW"

class MediaType(Enum):
    ALL = "Photos and animations"
    STATIC = "Photos only"
    ANIMATED = "Animations only (GIF/WebM)"