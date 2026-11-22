"""Генерация мира и логика проверок столкновений."""
import random
from .entities import Obstacle
from .models import GameMode, GameSettings, Position, Snake


class LevelGenerator:
    def __init__(self, rng: random.Random):
        self._rng = rng

    def free_cell(self, settings: GameSettings, occupied: set[Position]) -> Position | None:
        options = [Position(x, y)
                   for y in range(settings.height)
                   for x in range(settings.width)
                   if Position(x, y) not in occupied]
        return self._rng.choice(options) if options else None

    def initial_obstacles(self, settings: GameSettings, snake: Snake) -> list[Obstacle]:
        if settings.mode == GameMode.ZEN:
            return []
        number = 7 if settings.mode == GameMode.ARCADE else 15
        head = snake.head
        occupied = set(snake.segments)
        occupied.update(Position(x, y)
                        for x in range(max(0, head.x - 4), min(settings.width, head.x + 5))
                        for y in range(max(0, head.y - 3), min(settings.height, head.y + 4)))
        result = []
        for _ in range(number):
            pos = self.free_cell(settings, occupied)
            if pos is None:
                break
            occupied.add(pos)
            result.append(Obstacle(pos))
        return result


class CollisionSystem:
    """Проверяет столкновения, независимо от отображения и управляющего интерфейса."""

    @staticmethod
    def normalize(next_head: Position, settings: GameSettings) -> Position | None:
        if settings.mode == GameMode.ZEN:
            return Position(next_head.x % settings.width, next_head.y % settings.height)
        if 0 <= next_head.x < settings.width and 0 <= next_head.y < settings.height:
            return next_head
        return None

    @staticmethod
    def obstacle_hit(position: Position, obstacles: list[Obstacle]) -> bool:
        return any(obj.position == position for obj in obstacles)

    @staticmethod
    def body_hit(position: Position, snake: Snake, will_grow: bool) -> bool:
        # Хвост уходит при обычном ходе, поэтому его клетка допускается.
        occupied = snake.segments if will_grow else snake.segments[:-1]
        return position in occupied
