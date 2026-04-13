import random
import numpy as np
from typing import List, Tuple, Dict, Callable, Any

class StrategyGeneticOptimizer:
    """Genetic Algorithm for optimizing F1 pit stop strategies and tire compounds"""

    AVAILABLE_COMPOUNDS = ['SOFT', 'MEDIUM', 'HARD']

    def __init__(self, seed: int = 42):
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
        mutation_rate: float = 0.35
    ) -> Tuple[List[Dict], List[float]]:
        
        population = self._initialize_population(total_laps, population_size)
        fitness_history = []
        
        # --- NEW: The Hall of Fame ---
        # Tracks the absolute best pit timing for each unique tire sequence
        hall_of_fame = {} 

        print(f"GA: Starting evolution with population size {population_size} for {num_generations} generations")

        for generation in range(num_generations):
            fitness_scores = []
            evaluated_population = []

            for individual in population:
                num_stops = individual['num_stops']
                pit_laps = individual['pit_laps']
                compounds = individual['compounds']

                try:
                    fitness = fitness_function(num_stops, pit_laps, compounds)
                    fitness_scores.append(fitness)
                    evaluated_population.append((individual, fitness))
                    
                    # --- NEW: Update Hall of Fame ---
                    if fitness != float('inf'):
                        comp_tuple = tuple(compounds)
                        # If we've never seen this tire combo, or if this is the fastest version of it we've seen:
                        if comp_tuple not in hall_of_fame or fitness < hall_of_fame[comp_tuple]['fitness']:
                            hall_of_fame[comp_tuple] = {
                                'num_stops': num_stops,
                                'pit_laps': pit_laps.copy(),
                                'compounds': compounds.copy(),
                                'fitness': fitness
                            }

                except Exception as e:
                    fitness_scores.append(float('inf'))
                    evaluated_population.append((individual, float('inf')))

            evaluated_population.sort(key=lambda x: x[1])
            best_fitness = evaluated_population[0][1]
            fitness_history.append(best_fitness)

            if generation % 10 == 0:
                print(f"  Generation {generation}: Best fitness = {best_fitness:.2f}s")

            elite = [ind for ind, _ in evaluated_population[:elite_size]]
            new_population = elite.copy()

            while len(new_population) < population_size:
                parent1 = self._tournament_selection(evaluated_population)
                parent2 = self._tournament_selection(evaluated_population)

                child = self._crossover(parent1, parent2, total_laps)

                if random.random() < mutation_rate:
                    child = self._mutate(child, total_laps)

                new_population.append(child)

            population = new_population[:population_size]

        # --- NEW: Extract best from Hall of Fame instead of final generation ---
        # Sort the Hall of Fame by fitness (lowest time first)
        best_strategies = sorted(hall_of_fame.values(), key=lambda x: x['fitness'])
        
        # Grab the top 5 distinct tire strategies
        top_best_strategies = best_strategies[:5]

        print(f"GA: Evolution complete. Found {len(hall_of_fame)} total valid tire combos.")
        if top_best_strategies:
            print(f"GA: Best fitness overall: {top_best_strategies[0]['fitness']:.2f}s")

        return top_best_strategies, fitness_history

    def _initialize_population(self, total_laps: int, population_size: int) -> List[Dict]:
        population = []
        for _ in range(population_size):
            num_stops = random.choice([1, 2, 3])
            pit_laps = sorted(random.sample(range(5, total_laps - 5), num_stops))
            # Number of stints is always num_stops + 1
            compounds = [random.choice(self.AVAILABLE_COMPOUNDS) for _ in range(num_stops + 1)]

            population.append({
                'num_stops': num_stops,
                'pit_laps': pit_laps,
                'compounds': compounds
            })
        return population

    def _tournament_selection(self, evaluated_population: List[Tuple[Dict, float]], tournament_size: int = 3) -> Dict:
        tournament = random.sample(evaluated_population, min(tournament_size, len(evaluated_population)))
        winner = min(tournament, key=lambda x: x[1])
        return winner[0].copy()

    def _crossover(self, parent1: Dict, parent2: Dict, total_laps: int) -> Dict:
        pit_laps1 = parent1['pit_laps']
        pit_laps2 = parent2['pit_laps']
        comp1 = parent1['compounds']
        comp2 = parent2['compounds']

        # Mix pit laps
        if len(pit_laps1) > 0 and len(pit_laps2) > 0:
            combined_pits = sorted(list(set(pit_laps1[:len(pit_laps1)//2]) | set(pit_laps2[len(pit_laps2)//2:])))
            combined_pits = combined_pits[:3]
        else:
            combined_pits = pit_laps1 if len(pit_laps1) > len(pit_laps2) else pit_laps2
            
        num_stops = len(combined_pits)

        # Mix compounds
        combined_comps = comp1[:len(comp1)//2] + comp2[len(comp2)//2:]
        # Ensure compound length exactly matches (num_stops + 1)
        while len(combined_comps) < num_stops + 1:
            combined_comps.append(random.choice(self.AVAILABLE_COMPOUNDS))
        combined_comps = combined_comps[:num_stops + 1]

        return {
            'num_stops': num_stops,
            'pit_laps': combined_pits,
            'compounds': combined_comps
        }

    def _mutate(self, individual: Dict, total_laps: int) -> Dict:
        pit_laps = individual['pit_laps'].copy()
        compounds = individual['compounds'].copy()

        # Added 'change_tire' as a mutation option
        mutation_type = random.choice(['add', 'remove', 'shift', 'change_tire'])

        if mutation_type == 'add' and len(pit_laps) < 3:
            new_lap = random.randint(5, total_laps - 5)
            pit_laps.append(new_lap)
            pit_laps.sort()
            compounds.append(random.choice(self.AVAILABLE_COMPOUNDS))
            
        elif mutation_type == 'remove' and len(pit_laps) > 1:
            idx = random.randint(0, len(pit_laps) - 1)
            pit_laps.pop(idx)
            compounds.pop(idx) # Remove the tire compound for that stint
            
        elif mutation_type == 'shift' and len(pit_laps) > 0:
            idx = random.randint(0, len(pit_laps) - 1)
            new_lap = max(5, min(total_laps - 5, pit_laps[idx] + random.randint(-10, 10)))
            pit_laps[idx] = new_lap
            pit_laps.sort()
            
        elif mutation_type == 'change_tire':
            # Swap a tire compound for a random stint
            idx = random.randint(0, len(compounds) - 1)
            current = compounds[idx]
            others = [c for c in self.AVAILABLE_COMPOUNDS if c != current]
            compounds[idx] = random.choice(others)

        return {
            'num_stops': len(pit_laps),
            'pit_laps': pit_laps,
            'compounds': compounds
        }