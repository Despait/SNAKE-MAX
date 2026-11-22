"""Модели и перечисления игры «Змейка на максималках»."""
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    def is_opposite(self, other: "Direction") -> bool:
        return self.value[0] == -other.value[0] and self.value[1] == -other.value[1]


class GameMode(str, Enum):
    ARCADE = "Аркада"
    SURVIVAL = "Выживание"
    ZEN = "Дзен"


class Difficulty(str, Enum):
    EASY = "Легко"
    MEDIUM = "Нормально"
    HARD = "Сложно"


class GameState(str, Enum):
    READY = "Готов к игре"
    RUNNING = "Игра идёт"
    PAUSED = "Пауза"
    GAME_OVER = "Конец игры"


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def moved(self, direction: Direction) -> "Position":
        dx, dy = direction.value
        return Position(self.x + dx, self.y + dy)


@dataclass
class GameSettings:
    width: int = 26
    height: int = 19
    mode: GameMode = GameMode.ARCADE
    difficulty: Difficulty = Difficulty.MEDIUM

    @property
    def base_interval_ms(self) -> int:
        return {Difficulty.EASY: 180, Difficulty.MEDIUM: 135, Difficulty.HARD: 100}[self.difficulty]

    def __post_init__(self) -> None:
        if self.width < 8 or self.height < 8:
            raise ValueError("Игровое поле должно быть не меньше 8 × 8 клеток")


class Snake:
    """Инкапсуляция: сегменты, текущее и ожидающее направление закрыты от изменения."""

    def __init__(self, start: Position):
        self._segments = [start, Position(start.x - 1, start.y), Position(start.x - 2, start.y)]
        self._direction = Direction.RIGHT
        self._queued_direction: Direction | None = None

    @property
    def segments(self) -> tuple[Position, ...]:
        return tuple(self._segments)

    @property
    def head(self) -> Position:
        return self._segments[0]

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def next_head(self) -> Position:
        return self.head.moved(self._queued_direction or self._direction)

    def turn(self, direction: Direction) -> bool:
        """Не позволяет развернуться на 180° или обработать два поворота за один тик."""
        if direction == self._direction and self._queued_direction is None:
            return True
        if self._queued_direction is not None or direction.is_opposite(self._direction):
            return False
        self._queued_direction = direction
        return True

    def move(self, destination: Position, grow: bool = False) -> None:
        if self._queued_direction is not None:
            self._direction = self._queued_direction
        self._queued_direction = None
        self._segments.insert(0, destination)
        if not grow:
            self._segments.pop()
