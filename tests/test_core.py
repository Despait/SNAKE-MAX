"""Тесты игрового ядра. Запуск: python -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path
from snake_max.engine import GameEngine, ScoreManager
from snake_max.entities import DoublePoints, Food, GhostMode, GoldenFood, Obstacle, SlowMotion
from snake_max.models import Difficulty, Direction, GameMode, GameSettings, GameState, Position, Snake
from snake_max.world import CollisionSystem


class SnakeTests(unittest.TestCase):
    def test_initial_length_and_encapsulation(self):
        snake = Snake(Position(10, 10))
        self.assertEqual(len(snake.segments), 3)
        with self.assertRaises(AttributeError):
            snake.segments.append(Position(1, 1))

    def test_cannot_turn_back(self):
        snake = Snake(Position(10, 10))
        self.assertFalse(snake.turn(Direction.LEFT))
        self.assertTrue(snake.turn(Direction.UP))
        self.assertFalse(snake.turn(Direction.DOWN))
        self.assertFalse(snake.turn(Direction.LEFT))
        snake.move(snake.next_head)
        self.assertEqual(snake.direction, Direction.UP)

    def test_growth(self):
        snake = Snake(Position(10, 10))
        snake.move(Position(11, 10), grow=True)
        self.assertEqual(len(snake.segments), 4)
        snake.move(Position(12, 10))
        self.assertEqual(len(snake.segments), 4)


class EntityTests(unittest.TestCase):
    def test_food_polymorphism(self):
        engine = GameEngine(seed=21)
        items: list[Food] = [Food(Position(2, 2)), GoldenFood(Position(3, 3))]
        messages = [item.on_collect(engine) for item in items]
        self.assertEqual(engine.score, 60)
        self.assertEqual(engine.foods_eaten, 1)
        self.assertEqual(len(messages), 2)

    def test_powerup_polymorphism(self):
        engine = GameEngine(seed=22)
        for cls, key in [(DoublePoints, "double"), (GhostMode, "ghost"), (SlowMotion, "slow")]:
            bonus = cls(Position(3, 3))
            self.assertTrue(bonus.on_collect(engine))
            self.assertTrue(engine.effect_active(key))
        engine.add_score(10)
        self.assertEqual(engine.score, 20)


class EngineTests(unittest.TestCase):
    def test_initial_configuration(self):
        engine = GameEngine(GameSettings(mode=GameMode.ZEN), seed=10)
        self.assertEqual(engine.state, GameState.READY)
        self.assertFalse(engine.obstacles)
        self.assertFalse(engine.portals)
        self.assertIsNotNone(engine.food)

    def test_zen_wrap(self):
        settings = GameSettings(width=8, height=8, mode=GameMode.ZEN)
        self.assertEqual(CollisionSystem.normalize(Position(8, 2), settings), Position(0, 2))
        self.assertEqual(CollisionSystem.normalize(Position(-1, 5), settings), Position(7, 5))
        settings.mode = GameMode.ARCADE
        self.assertIsNone(CollisionSystem.normalize(Position(8, 2), settings))

    def test_food_grows_on_step(self):
        engine = GameEngine(GameSettings(mode=GameMode.ZEN), seed=30)
        engine.food = Food(engine.snake.next_head)
        engine.start()
        engine.step()
        self.assertEqual(engine.foods_eaten, 1)
        self.assertEqual(engine.score, 10)
        self.assertEqual(len(engine.snake.segments), 4)

    def test_wall_collision(self):
        engine = GameEngine(GameSettings(width=8, height=8, mode=GameMode.ARCADE), seed=12)
        engine.obstacles = []
        engine.portals = []
        engine.food = Food(Position(1, 1))
        engine.start()
        for _ in range(6):
            engine.step()
        self.assertEqual(engine.state, GameState.GAME_OVER)

    def test_obstacle_collision_and_ghost(self):
        engine = GameEngine(GameSettings(mode=GameMode.ARCADE), seed=43)
        target = engine.snake.next_head
        engine.obstacles = [Obstacle(target)]
        engine.portals = []
        engine.food = Food(Position(1, 1))
        engine.start()
        engine.apply_effect("ghost", 4)
        engine.step()
        self.assertEqual(engine.state, GameState.RUNNING)
        self.assertEqual(engine.snake.head, target)
        engine2 = GameEngine(GameSettings(mode=GameMode.ARCADE), seed=43)
        engine2.obstacles = [Obstacle(engine2.snake.next_head)]
        engine2.portals = []
        engine2.start()
        engine2.step()
        self.assertEqual(engine2.state, GameState.GAME_OVER)

    def test_pause_prevents_movement(self):
        engine = GameEngine(seed=5)
        engine.start()
        old = engine.snake.head
        engine.toggle_pause()
        engine.step()
        self.assertEqual(engine.snake.head, old)
        engine.toggle_pause()
        self.assertEqual(engine.state, GameState.RUNNING)

    def test_settings_validate(self):
        with self.assertRaises(ValueError):
            GameSettings(width=3)


class ScoreTests(unittest.TestCase):
    def test_persistence_and_sorting(self):
        with tempfile.TemporaryDirectory() as temp:
            mgr = ScoreManager(Path(temp) / "records.json")
            mgr.save("Катя", 25, GameMode.ZEN, Difficulty.EASY)
            mgr.save("Денис", 50, GameMode.ARCADE, Difficulty.HARD)
            scores = mgr.load()
            self.assertEqual([r["score"] for r in scores], [50, 25])
            self.assertEqual(scores[1]["name"], "Катя")


if __name__ == "__main__":
    unittest.main()
