# services/ingestion/domains/roles/dtos.py
from enum import IntEnum


class Role(IntEnum):
    """Позиції гравців у Dota 2 (1–5).

    Використовується як universal taxonomy — не прив'язана до жодного провайдера.
    Числові значення відповідають класичній нумерації позицій.
    """

    CARRY = 1        # safe lane core
    MID = 2          # middle lane core
    OFFLANE = 3      # hard lane core
    SUPPORT = 4      # soft support (position 4)
    HARD_SUPPORT = 5  # hard support (position 5)