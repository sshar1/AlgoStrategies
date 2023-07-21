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

        if game_state.turn_number >= 3 and attacking:
            if game_state.contains_stationary_unit([1, 13]):
                game_state.attempt_remove([1, 13])
                return

            self.infiltrate(game_state)

    # Base defense of turrets, walls, interceptors, and supports
    def base_funnel(self, game_state, attacking):

        # Base wall
        self.place_base_walls(game_state, attacking)

        # Turrets
        self.place_turrets(game_state)

        # Supports
        if game_state.get_resource(SP, 0) >= 4:
            self.place_supports(game_state)

    def place_base_walls(self, game_state, attacking):
        left = [[0, 13], [2, 13], [3, 13], [4, 12], [5, 11], [6, 11], [7, 10], [8, 10], [10, 10], [11, 9], [12, 8], [13, 8]]
        right = [[27, 13], [26, 13], [25, 13], [24, 13], [23, 12], [22, 11], [21, 11], [20, 10], [19, 10], [17, 10], [16, 9], [14, 8], [15, 8]]

        locations = left + right

        if not attacking:
            locations.append([1, 13])

        game_state.attempt_spawn(WALL, locations)

        upgrade_locations = []
        if game_state.turn_number >= 6:
            for location in locations:
                if game_state.contains_stationary_unit(location):
                    if game_state.game_map[location[0], location[1]][0].health < 80 and game_state.game_map[location[0], location[1]][0].upgraded:
                        game_state.attempt_remove(location)
                    elif not game_state.game_map[location[0], location[1]][0].upgraded:
                        upgrade_locations.append(location)

        if game_state.get_resource(SP, 0) > len(upgrade_locations) and game_state.turn_number >= 3:
            game_state.attempt_upgrade(upgrade_locations)

    def place_turrets(self, game_state):
        turret_locations = [[18, 10], [9, 10]] # Main center turrets
        if game_state.turn_number >= 6 and game_state.get_resource(SP, 0) >= 4:
            turret_locations.append([3, 12])
            turret_locations.append([24, 12])
        if game_state.turn_number >= 8 and game_state.get_resource(SP, 0) >= 8:
            turret_locations.append([7, 12])
            turret_locations.append([20, 12])
            
        game_state.attempt_spawn(TURRET, turret_locations)

        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number >= 6:
            game_state.attempt_upgrade(turret_locations)

    def place_supports(self, game_state):
        support_locations = []
        if game_state.turn_number >= 4:
            support_locations.append([7, 9])
            support_locations.append([8, 9])
        if game_state.turn_number >= 6:
            support_locations.append([7, 8])
            support_locations.append([8, 8])

        game_state.attempt_spawn(SUPPORT, support_locations)

        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number >= 6:
            game_state.attempt_upgrade(support_locations)

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def infiltrate(self, game_state):
        if game_state.get_resource(MP, 0) < 13: return

        suicide_interceptor_location = [3, 10]
        suicide_interceptor_num = 4
        
        max_health = 0
        if game_state.contains_stationary_unit([1, 14]):
            max_health = game_state.game_map[1, 14][0].health
        if game_state.contains_stationary_unit([0, 14]):
            h = game_state.game_map[0, 14][0].health
            max_health = h if h > max_health else max_health
        
        if max_health <= 60:
            suicide_interceptor_num = 3

        attacker_scout_location = [14, 0]
        attacker_scout_num = trunc(game_state.get_resource(MP, 0) - suicide_interceptor_num)

        for _ in range(suicide_interceptor_num):
            game_state.attempt_spawn(INTERCEPTOR, suicide_interceptor_location)
        for _ in range(attacker_scout_num):
            game_state.attempt_spawn(SCOUT, attacker_scout_location)

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
