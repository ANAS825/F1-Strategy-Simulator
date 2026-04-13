"""
Genetic Algorithm-based Strategy Optimizer
Evolves pit stop strategies to find optimal combinations instead of brute force.
"""

import numpy as np
from typing import List, Dict, Callable, Tuple
import random


class StrategyGeneticOptimizer:
    """
    Uses genetic algorithm to optimize F1 pit stop strategies.

    Genes: pit stop count (1-4) and timing (which lap to stop)
    Fitness: Total race time (lower is better)
    """

    def __init__(self, seed: int = None):
        """Initialize optimizer with random seed for reproducibility."""
        if seed is None:
            seed = np.random.randint(0, 10000)  # Use random seed for diverse results
        random.seed(seed)
        np.random.seed(seed)
        self.seed = seed
        self.best_fitness_history = []

    def encode_strategy(self, num_stops: int, pit_laps: List[int]) -> List[int]:
        """
        Encode a strategy as a gene (list of ints).
        Gene format: [num_stops, pit_lap1, pit_lap2, pit_lap3, ...]

        Args:
            num_stops: Number of pit stops (1-3)
            pit_laps: List of lap numbers for each pit stop

        Returns:
            Encoded gene
        """
        gene = [num_stops] + sorted(pit_laps)[:num_stops]
        # Pad to fixed length (3 stops max)
        while len(gene) < 4:
            gene.append(0)
        return gene[:4]

    def decode_strategy(self, gene: List[int], total_laps: int) -> Tuple[int, List[int]]:
        """
        Decode a gene back to strategy parameters.

        Returns:
            (num_stops, pit_laps)
        """
        num_stops = gene[0]
        pit_laps = sorted([p for p in gene[1:num_stops + 1] if p > 0])
        return (num_stops, pit_laps)

    def generate_initial_population(self, population_size: int, total_laps: int) -> List[List[int]]:
        """
        Generate initial population of random strategies with diverse pit windows.
        """
        population = []
        strategies_created = set()

        for _ in range(population_size):
            # Vary strategy to create diversity
            num_stops = random.randint(1, 3)
            strategy_variant = random.randint(0, 2)  # Different pit timing philosophies

            if num_stops == 1:
                # 1-stop: varied pit windows
                if strategy_variant == 0:
                    # Early pit (aggressive)
                    pit_lap = random.randint(int(total_laps * 0.25), int(total_laps * 0.4))
                elif strategy_variant == 1:
                    # Mid pit (balanced)
                    pit_lap = random.randint(int(total_laps * 0.4), int(total_laps * 0.6))
                else:
                    # Late pit (conservative)
                    pit_lap = random.randint(int(total_laps * 0.55), int(total_laps * 0.75))
                pit_laps = [pit_lap]

            elif num_stops == 2:
                # 2-stop: varied split strategies
                if strategy_variant == 0:
                    # Early double pit
                    pit1 = random.randint(int(total_laps * 0.2), int(total_laps * 0.35))
                    pit2 = random.randint(int(total_laps * 0.55), int(total_laps * 0.7))
                elif strategy_variant == 1:
                    # Balanced double pit
                    pit1 = random.randint(int(total_laps * 0.3), int(total_laps * 0.4))
                    pit2 = random.randint(int(total_laps * 0.6), int(total_laps * 0.75))
                else:
                    # Late double pit
                    pit1 = random.randint(int(total_laps * 0.35), int(total_laps * 0.48))
                    pit2 = random.randint(int(total_laps * 0.65), int(total_laps * 0.8))
                pit_laps = [pit1, pit2]

            else:  # 3-stop
                # 3-stop: varied triple pit strategies
                if strategy_variant == 0:
                    # Early triple pit strategy
                    pit1 = random.randint(int(total_laps * 0.12), int(total_laps * 0.25))
                    pit2 = random.randint(int(total_laps * 0.38), int(total_laps * 0.5))
                    pit3 = random.randint(int(total_laps * 0.72), int(total_laps * 0.85))
                elif strategy_variant == 1:
                    # Balanced triple pit strategy
                    pit1 = random.randint(int(total_laps * 0.15), int(total_laps * 0.28))
                    pit2 = random.randint(int(total_laps * 0.45), int(total_laps * 0.58))
                    pit3 = random.randint(int(total_laps * 0.7), int(total_laps * 0.85))
                else:
                    # Late first pit, then aggressive
                    pit1 = random.randint(int(total_laps * 0.22), int(total_laps * 0.35))
                    pit2 = random.randint(int(total_laps * 0.5), int(total_laps * 0.62))
                    pit3 = random.randint(int(total_laps * 0.75), int(total_laps * 0.88))
                pit_laps = [pit1, pit2, pit3]

            gene = self.encode_strategy(num_stops, pit_laps)
            gene_tuple = tuple(gene)

            # Avoid duplicates
            if gene_tuple not in strategies_created:
                population.append(gene)
                strategies_created.add(gene_tuple)

        # Fill remaining population if we had duplicates
        while len(population) < population_size:
            num_stops = random.randint(1, 3)
            min_gap = int(total_laps * 0.1)

            if num_stops == 1:
                pit_lap = random.randint(int(total_laps * 0.25), int(total_laps * 0.75))
                pit_laps = [pit_lap]
            elif num_stops == 2:
                pit1 = random.randint(int(total_laps * 0.2), int(total_laps * 0.45))
                pit2 = random.randint(pit1 + min_gap, int(total_laps * 0.8))
                pit_laps = [pit1, pit2]
            else:
                pit1 = random.randint(int(total_laps * 0.12), int(total_laps * 0.35))
                pit2 = random.randint(pit1 + min_gap, int(total_laps * 0.6))
                pit3 = random.randint(pit2 + min_gap, int(total_laps * 0.88))
                pit_laps = [pit1, pit2, pit3]

            gene = self.encode_strategy(num_stops, pit_laps)
            gene_tuple = tuple(gene)
            if gene_tuple not in strategies_created:
                population.append(gene)
                strategies_created.add(gene_tuple)

        return population

    def mutate_gene(self, gene: List[int], total_laps: int, mutation_rate: float = 0.2) -> List[int]:
        """
        Apply mutation to a gene with varying severity.
        """
        mutated = gene.copy()

        # Number of stops mutation
        if random.random() < mutation_rate:
            mutated[0] = max(1, min(3, mutated[0] + random.randint(-1, 1)))

        # Pit lap time mutations with varied severity
        for i in range(1, 4):
            if random.random() < mutation_rate * 1.5 and mutated[0] >= i:
                # 70% chance: small shift (±5-15 laps)
                if random.random() < 0.7:
                    shift = random.randint(-15, 15)
                # 20% chance: medium shift (±20-40 laps)
                elif random.random() < 0.67:
                    shift = random.randint(-40, 40)
                # 10% chance: large shift (±50-100 laps)
                else:
                    shift = random.randint(-100, 100)

                mutated[i] = max(5, min(total_laps - 5, mutated[i] + shift))

        return mutated

    def crossover_genes(self, gene1: List[int], gene2: List[int]) -> Tuple[List[int], List[int]]:
        """
        Combine two genes to create offspring (single-point crossover).
        """
        crossover_point = random.randint(1, 3)

        offspring1 = gene1[:crossover_point] + gene2[crossover_point:]
        offspring2 = gene2[:crossover_point] + gene1[crossover_point:]

        return (offspring1, offspring2)

    def evolve_strategies(
        self,
        fitness_function: Callable[[int, List[int]], float],
        total_laps: int,
        population_size: int = 20,
        num_generations: int = 50,
        elite_size: int = 4,
        mutation_rate: float = 0.2
    ) -> Tuple[List[Dict], List[float]]:
        """
        Main genetic algorithm evolution loop.

        Args:
            fitness_function: Function that takes (num_stops, pit_laps) and returns total_time
            total_laps: Total laps in race
            population_size: Size of population to evolve
            num_generations: Number of generations to evolve
            elite_size: Number of top strategies to preserve each generation
            mutation_rate: Probability of mutation per gene

        Returns:
            (evolved_strategies, fitness_history)
            evolved_strategies: List of best strategies found
            fitness_history: Best fitness per generation
        """
        population = self.generate_initial_population(population_size, total_laps)
        best_fitness_history = []

        print(f"\n--- Genetic Algorithm Optimization ---")
        print(f"Population: {population_size}, Generations: {num_generations}\n")

        for generation in range(num_generations):
            # Evaluate fitness
            fitnesses = []
            for gene in population:
                num_stops, pit_laps = self.decode_strategy(gene, total_laps)
                if pit_laps and len(pit_laps) <= 3:
                    try:
                        fitness = fitness_function(num_stops, pit_laps)
                        fitnesses.append(fitness)
                    except:
                        fitnesses.append(float('inf'))
                else:
                    fitnesses.append(float('inf'))

            # Sort by fitness (lower is better)
            population_with_fitness = list(zip(population, fitnesses))
            population_with_fitness.sort(key=lambda x: x[1])

            best_fitness = population_with_fitness[0][1]
            best_fitness_history.append(best_fitness)

            avg_fitness = float(np.mean([f for f in fitnesses if f != float('inf')]))
            print(f"Gen {generation + 1:3d}: Best Time = {best_fitness:7.2f}s | Avg = {avg_fitness:7.2f}s")

            if generation < num_generations - 1:
                # Selection: take elite + select rest by tournament
                elite = [gene for gene, _ in population_with_fitness[:elite_size]]

                population = elite.copy()

                # Tournament selection for remaining
                while len(population) < population_size:
                    # Select best of 3 random candidates
                    candidates = random.sample(range(len(population_with_fitness)), min(3, len(population_with_fitness)))
                    best_idx = min(candidates, key=lambda idx: population_with_fitness[idx][1])
                    parent = population_with_fitness[best_idx][0].copy()

                    # Apply crossover with elite
                    if random.random() < 0.8 and len(elite) > 1:
                        elite_partner = random.choice(elite)
                        child1, child2 = self.crossover_genes(parent, elite_partner)
                        population.append(self.mutate_gene(child1, total_laps, mutation_rate))
                    else:
                        population.append(self.mutate_gene(parent, total_laps, mutation_rate))

        # Return top strategies
        best_strategies = []
        for gene, fitness in population_with_fitness[:5]:  # Top 5
            num_stops, pit_laps = self.decode_strategy(gene, total_laps)
            if pit_laps and len(pit_laps) <= 3:
                best_strategies.append({
                    'num_stops': num_stops,
                    'pit_laps': pit_laps,
                    'fitness': fitness,
                    'gene': gene
                })

        print(f"\n[OK] Optimization complete. Top strategy: {best_fitness_history[-1]:.2f}s")
        return best_strategies, best_fitness_history
