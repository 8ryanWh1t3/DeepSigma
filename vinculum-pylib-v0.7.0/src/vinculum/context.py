"""Optional narrative framing. No probability, numeric order, hinge or score belongs here."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NarrativeContext:
    title: str
    origin_path: tuple[str, ...]
    retreat_path: tuple[str, ...]
    attribution: str = "User's philosophical/theological framing; not a scientific inference or scored claim."

    def __post_init__(self):
        object.__setattr__(self, 'origin_path', tuple(self.origin_path))
        object.__setattr__(self, 'retreat_path', tuple(self.retreat_path))
        if not self.title or not self.attribution:
            raise ValueError('narrative needs title and attribution')

    @classmethod
    def deep_sigma(cls):
        return cls('From origin to representation; from description to presence',
                   ('God', 'Big Bang', 'Nature / physical reality', 'Cellular / divisional reality',
                    'Human experience', 'Language and mathematics as representations'),
                   ('Names, numbers and divisions', 'Human experience', 'Nature',
                    'Stillness before description', 'God'))
