from ...core import _ITERATOR_CORE_STATE


class IteratorCounter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "iterator_id": ("STRING", {"default": "counter_iterator"}),
                "start": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "max_iterations": (
                    "INT",
                    {"default": 10, "min": 1, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "step": ("INT", {"default": 1, "min": 1, "max": 0xFFFFFFFFFFFFFFFF}),
                "reset": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("INT", "BOOLEAN")
    RETURN_NAMES = ("current_count", "is_finished")
    FUNCTION = "increment"
    CATEGORY = "Iterator"

    @classmethod
    def IS_CHANGED(s, iterator_id, **kwargs):
        return _ITERATOR_CORE_STATE.get(iterator_id, 0)

    def increment(self, iterator_id, start, max_iterations, step, reset):
        global _ITERATOR_CORE_STATE

        if reset:
            _ITERATOR_CORE_STATE[iterator_id] = 0

        idx = _ITERATOR_CORE_STATE.get(iterator_id, 0)
        current_count = start + (idx * step)
        is_finished = (idx + 1) >= max_iterations

        return (current_count, is_finished)
