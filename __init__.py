from .nodes.iterator.iterator_counter import IteratorCounter
from .nodes.iterator.iterator_item import IteratorItem
from .nodes.iterator.iterator_list import IteratorList
from .nodes.iterator.iterator_signal import IteratorSignal
from .nodes.video_concatenation.video_concatenation import VideoConcatenation

NODE_CLASS_MAPPINGS = {
    "IteratorCounter": IteratorCounter,
    "IteratorItem": IteratorItem,
    "IteratorList": IteratorList,
    "IteratorSignal": IteratorSignal,
    "VideoConcatenation": VideoConcatenation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "IteratorCounter": "Iterator Counter",
    "IteratorItem": "Iterator Item",
    "IteratorList": "Iterator List",
    "IteratorSignal": "Iterator Signal",
    "VideoConcatenation": "Video Concatenation",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
