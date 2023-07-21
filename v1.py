import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from math import *
import copy

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        self.hypothetical_state = gamelib.GameState(self.config, turn_state)
        self.game_state = game_state
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):

        attacking = game_state.get_resource(MP, 0) >= 13

        # First, place basic defenses
        self.base_funnel(game_state, attacking)

        if game_state.turn_number >= 4 and attacking:
            if game_state.contains_stationary_unit([0, 13]) or game_state.contains_stationary_unit([1, 13]):
                game_state.attempt_remove([[0, 13], [1, 13]])
                return

            self.scout_spam(game_state)

    def should_spawn_scouts(self, game_state, damage_taken):
        if damage_taken == 0: return True

        num_scouts = self.get_attacker_scout_count(game_state)

        return ((num_scouts * 17) / damage_taken) >= 0.7

    def should_spawn_demolishers(self, game_state, damage_taken):
        if damage_taken == 0: return True

        num_demolishers = self.get_demolisher_count(game_state)

        return ((num_demolishers * 5) / damage_taken) >= 0.02

    # Base defense of turrets, walls, interceptors, and supports
    def base_funnel(self, game_state, attacking):

        # Base wall
        self.place_base_walls(game_state, attacking)

        # Turrets
        self.place_turrets(game_state)

        # Supports
        if game_state.get_resource(SP, 0) >= 4:
            self.place_supports(game_state)

        # Interceptors
        if game_state.turn_number < 4:
            self.spawn_interceptors(game_state)

    def place_base_walls(self, game_state, attacking):
        left = [[2, 13], [3, 13], [4, 12], [5, 11], [6, 11], [8, 10], [10, 10], [11, 9], [13, 8]]
        right = [[27, 13], [26, 13], [25, 13], [24, 13], [23, 12], [22, 11], [21, 11], [19, 10], [17, 10], [16, 9], [14, 8]]

        locations = left + right

        if not attacking:
            locations.append([0, 13])
            locations.append([1, 13])

        if game_state.turn_number >= 4:
            locations.append([7, 10])
            locations.append([20, 10])

        game_state.attempt_spawn(WALL, locations)

        price = 0
        upgrade_locations = []
        for location in locations:
            if game_state.contains_stationary_unit(location):
                if game_state.game_map[locaiton[0], location[1]].health < 80:
                    game_state.attempt_remove(location)
                elif game_state.game_map[location[0], location[1]].upgraded:
                    upgrade_locations.append(location)

        if game_state.get_resource(SP, 0) > len(upgrade_locations) and game_state.turn_number >= 7:
            game_state.attempt_upgrade(upgrade_locations)

    def place_turrets(self, game_state):
        turret_locations = [[18, 10], [9, 10]] # Main center turrets
        secondary_locations = [[15, 8], [12, 8]] # Close center turrets
        if game_state.turn_number >= 6 and game_state.get_resource(SP, 0) >= 4:
            turret_locations.append([3, 12])
            turret_locations.append([24, 12])
        if game_state.turn_number >= 8 and game_state.get_resource(SP, 0) >= 8:
            turret_locations.append([7, 12])
            turret_locations.append([20, 12])
            
        game_state.attempt_spawn(TURRET, turret_locations)
        game_state.attempt_spawn(TURRET, secondary_locations)

        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number >= 3:
            game_state.attempt_upgrade(turret_locations)

    def place_supports(self, game_state):
        support_locations = []
        if game_state.turn_number >= 4:
            support_locations.append([15, 7])
            support_locations.append([16, 7])
        if game_state.turn_number >= 6:
            support_locations.append([16, 8])
            support_locations.append([17, 8])
        if game_state.turn_number >= 10:
            support_locations.append([17, 9])

        game_state.attempt_spawn(SUPPORT, support_locations)

        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number >= 10:
            game_state.attempt_upgrade(support_locations)

    def spawn_interceptors(self, game_state):
        num_interceptors = 1
        interceptor_locations = [[4, 9], [23, 9]]
        
        for _ in range(num_interceptors):
            game_state.attempt_spawn(INTERCEPTOR, interceptor_locations)

    # Returns the spawn point that will receive the least damage and the damage at that point
    def least_damage_spawn(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)

        damages = []
        for location in deploy_locations:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path[8:]: # Ignore first 8 path locations
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        return deploy_locations[damages.index(min(damages))], min(damages)

    def get_damage_at_spawn(self, game_state, spawn):
        path = game_state.find_path_to_edge(spawn)
        damage = 0
        for path_location in path:
            damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i

        return damage

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_attacker_scout_count(self, game_state):
        return trunc(game_state.get_resource(MP, 0) - 7)

    def demolisher_spam(self, game_state, location):
        demolisher_count = self.get_demolisher_count(game_state)
        if demolisher_count <= 3: return

        for _ in range(demolisher_count):
            game_state.attempt_spawn(DEMOLISHER, location)

    def get_demolisher_count(self, game_state):
        return trunc(game_state.get_resource(MP, 0) / 3)

    def scout_spam(self, game_state):
        if game_state.get_resource(MP, 0) < 13: return

        suicide_scout_location = [14, 0]
        suicide_scout_num = 7

        attacker_scout_location = [21, 7]
        attacker_scout_num = trunc(game_state.get_resource(MP, 0) - suicide_scout_num)

        for _ in range(suicide_scout_num):
            game_state.attempt_spawn(SCOUT, suicide_scout_location)
        for _ in range(attacker_scout_num):
            game_state.attempt_spawn(SCOUT, attacker_scout_location)

    def get_location_side(self, game_state, location):
        if location[0] < 14:
            return game_state.game_map.TOP_LEFT
        return game_state.game_map.TOP_RIGHT

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        spawns = events["spawn"]

        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
