"""JSON-only Redis values for temporary authentication state and counters."""

import json


class AuthStateJSONSerializer:
    def dumps(self, value):
        # Redis INCR must see a plain integer for atomic shared attempt limits.
        if type(value) is int:
            return value
        return json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def loads(self, value):
        # Never deserialize executable pickle data from a network cache.
        return json.loads(value)
