"""
Genetic Algorithm Optimizer for F1 Strategy Selection
Finds optimal pit stop timing and tire combinations
"""

import random
import numpy as np
from typing import List, Tuple, Dict, Callable, Any


class StrategyGeneticOptimizer:
    """Genetic Algorithm for optimizing F1 pit stop strategies"""

    def __init__(self, seed: int = 42):
        """
        Initialize the optimizer

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def evolve_strategies(
        self,
        fitness_function: Callable,
        total_laps: int,
        population_size: int = 20,
        num_generations: int = 30,
        elite_size: int = 4,
        mutation_rate: float = 0.3
    ) -> Tuple[List[Dict], List[float]]:
        """
        Run genetic algorithm to evolve strategies

        Args:
            fitness_function: Function that takes (num_stops, pit_laps) and returns fitness (lower is better)
            total_laps: Total laps in the race
            population_size: Size of population per generation
            num_generations: Number of generations to evolve
            elite_size: Number of best strategies to preserve
            mutation_rate: Probability of mutation

        Returns:
            Tuple of (best_strategies, fitness_history)
        """

        # Initialize population with random pit stop strategies
        population = self._initialize_population(total_laps, population_size)
        fitness_history = []

        print(f"GA: Starting evolution with population size {population_size} for {num_generations} generations")

        for generation in range(num_generations):
            # Evaluate fitness for current population
            fitness_scores = []
            evaluated_population = []

            for individual in population:
                num_stops = individual['num_stops']
                pit_laps = individual['pit_laps']

                try:
                    fitness = fitness_function(num_stops, pit_laps)
                    fitness_scores.append(fitness)
                    evaluated_population.append((individual, fitness))
                except:
                    fitness_scores.append(float('inf'))
                    evaluated_population.append((individual, float('inf')))

            # Sort by fitness (lower is better)
            evaluated_population.sort(key=lambda x: x[1])
            best_fitness = evaluated_population[0][1]
            fitness_history.append(best_fitness)

            if generation % 10 == 0:
                print(f"  Generation {generation}: Best fitness = {best_fitness:.2f}s")

            # Select elite (best performing individuals)
            elite = [ind for ind, _ in evaluated_population[:elite_size]]

            # Create new population through selection and crossover
            new_population = elite.copy()  # Keep elite

            while len(new_population) < population_size:
                # Tournament selection
                parent1 = self._tournament_selection(evaluated_population)
                parent2 = self._tournament_selection(evaluated_population)

                # Crossover
                child = self._crossover(parent1, parent2, total_laps)

                # Mutation
                if random.random() < mutation_rate:
                    child = self._mutate(child, total_laps)

                new_population.append(child)

            population = new_population[:population_size]

        # Return best strategies found
        best_strategies = [
            {
                'num_stops': ind['num_stops'],
                'pit_laps': ind['pit_laps'],
                'fitness': fitness
            }
            for ind, fitness in evaluated_population[:min(5, len(evaluated_population))]
        ]

        print(f"GA: Evolution complete. Best fitness: {best_strategies[0]['fitness']:.2f}s")

        return best_strategies, fitness_history

    def _initialize_population(self, total_laps: int, population_size: int) -> List[Dict]:
        """Initialize population with random pit stop strategies"""
        population = []

        for _ in range(population_size):
            # Randomly choose 1, 2, or 3 pit stops
            num_stops = random.choice([1, 2, 3])

            # Generate random pit lap times
            pit_laps = sorted(random.sample(range(5, total_laps - 5), num_stops))

            population.append({
                'num_stops': num_stops,
                'pit_laps': pit_laps
            })

        return population

    def _tournament_selection(self, evaluated_population: List[Tuple[Dict, float]], tournament_size: int = 3) -> Dict:
        """Select individual using tournament selection"""
        tournament = random.sample(evaluated_population, min(tournament_size, len(evaluated_population)))
        winner = min(tournament, key=lambda x: x[1])
        return winner[0].copy()

    def _crossover(self, parent1: Dict, parent2: Dict, total_laps: int) -> Dict:
        """Crossover operation between two parents"""
        # Combine pit laps from both parents
        pit_laps1 = parent1['pit_laps']
        pit_laps2 = parent2['pit_laps']

        # Random crossover point
        if len(pit_laps1) > 0 and len(pit_laps2) > 0:
            # Mix pit laps from both parents
            combined_pits = sorted(list(set(pit_laps1[:len(pit_laps1)//2]) | set(pit_laps2[len(pit_laps2)//2:])))
            # Limit to 3 pit stops max
            combined_pits = combined_pits[:3]
        else:
            combined_pits = pit_laps1 if len(pit_laps1) > len(pit_laps2) else pit_laps2

        return {
            'num_stops': len(combined_pits),
            'pit_laps': combined_pits
        }

    def _mutate(self, individual: Dict, total_laps: int) -> Dict:
        """Mutate an individual"""
        pit_laps = individual['pit_laps'].copy()

        mutation_type = random.choice(['add', 'remove', 'shift'])

        if mutation_type == 'add' and len(pit_laps) < 3:
            # Add new pit stop
            new_lap = random.randint(5, total_laps - 5)
            pit_laps.append(new_lap)
            pit_laps.sort()

        elif mutation_type == 'remove' and len(pit_laps) > 1:
            # Remove pit stop
            pit_laps.pop(random.randint(0, len(pit_laps) - 1))

        elif mutation_type == 'shift' and len(pit_laps) > 0:
            # Shift pit stop timing
            idx = random.randint(0, len(pit_laps) - 1)
            new_lap = max(5, min(total_laps - 5, pit_laps[idx] + random.randint(-10, 10)))
            pit_laps[idx] = new_lap
            pit_laps.sort()

        return {
            'num_stops': len(pit_laps),
            'pit_laps': pit_laps
        }
