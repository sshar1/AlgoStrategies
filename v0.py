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
        self.current_infiltrator_wall_side = None
        self.counter_infiltrator_strat = False
        self.last_enemy_spawn_update = []
        self.game_state = None

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
        # First, place basic defenses
        self.base_funnel(game_state)

        # This is extremely messy, but it's just temporary
        safest_spawn, least_damage = self.least_damage_spawn(game_state)
        path_blocked, end_location = self.wall_blocking_path(game_state, safest_spawn)
        if (path_blocked and game_state.turn_number > 6) or self.counter_infiltrator_strat:
            counter_infiltrator_strat = True
            wall_side = self.get_location_side(game_state, end_location)
            if self.current_infiltrator_wall_side is None:
                self.current_infiltrator_wall_side = wall_side
            elif self.current_infiltrator_wall_side != wall_side:
                if self.current_infiltrator_wall_side == game_state.game_map.TOP_LEFT:
                    self.clear_infiltrator_counter_walls(game_state, game_state.game_map.BOTTOM_LEFT)
                else:
                    self.clear_infiltrator_counter_walls(game_state, game_state.game_map.BOTTOM_RIGHT)
                self.current_infiltrator_wall_side = wall_side
                return
            if wall_side == game_state.game_map.TOP_LEFT:
                self.place_infiltrator_counter_walls(game_state, game_state.game_map.BOTTOM_LEFT)
                self.spawn_infiltrator_scouts(game_state, game_state.game_map.BOTTOM_LEFT)
            else:
                self.place_infiltrator_counter_walls(game_state, game_state.game_map.BOTTOM_RIGHT)
                self.spawn_infiltrator_scouts(game_state, game_state.game_map.BOTTOM_RIGHT)
        else:
            if self.should_spawn_scouts(game_state, least_damage):
                gamelib.debug_write('spawning scouts...')
                self.scout_spam(game_state, safest_spawn)
            elif self.should_spawn_demolishers(game_state, least_damage):
                self.demolisher_spam(game_state, safest_spawn)

    def should_spawn_scouts(self, game_state, damage_taken):
        if damage_taken == 0: return True

        num_scouts = self.get_scout_count(game_state)

        return ((num_scouts * 17) / damage_taken) >= 4

    def should_spawn_demolishers(self, game_state, damage_taken):
        if damage_taken == 0: return True

        num_demolishers = self.get_scout_count(game_state)

        return ((num_demolishers * 5) / damage_taken) >= 0.5

    # Base defense of turrets, walls, interceptors, and supports
    def base_funnel(self, game_state):
        
        left_side = [[0, 13], [1, 12], [2, 11], [3, 10]]
        right_side = [[27, 13], [26, 12], [25, 11], [24, 10]]

        if any(location in self.scored_on_locations for location in left_side):
            self.place_infiltrator_walls(game_state, 'left')
        if any(location in self.scored_on_locations for location in right_side):
            self.place_infiltrator_walls(game_state, 'right')

        # Base wall
        self.place_base_walls(game_state)

        # Turrets
        self.place_turrets(game_state)

        # Extra funnel walls
        wall_locations = [[10, 10], [17, 10], [11, 9], [16, 9], [13, 8], [14, 8]]
        game_state.attempt_spawn(WALL, wall_locations)

        # Supports
        if game_state.get_resource(SP, 0) >= 4:
            self.place_supports(game_state)

        # Interceptors
        if (game_state.turn_number < 10 and game_state.get_resource(MP, 1) > 10) or game_state.turn_number < 3:
            self.spawn_interceptors(game_state)

    def place_base_walls(self, game_state):
        for i in range(10):
            game_state.attempt_spawn(WALL, [i, 13])
            if game_state.turn_number > 12 and game_state.get_resource(SP, 0) > 15 and (i < 3 or i > 7):
                game_state.attempt_upgrade([i, 13])
        for i in range(27, 17, -1):
            game_state.attempt_spawn(WALL, [i, 13])
            if game_state.turn_number > 12 and game_state.get_resource(SP, 0) > 15 and (i < 20 or i > 24):
                game_state.attempt_upgrade([i, 13])

    def place_infiltrator_walls(self, game_state, side):
        left = [[0, 13], [1, 13], [1, 12], [2, 12]]
        right = [[27, 13], [26, 13], [26, 12], [25, 12]]

        locations = None
        if side == 'left':
            locations = left
        else:
            locations = right

        game_state.attempt_spawn(WALL, locations)
        game_state.attempt_upgrade(locations)

    def place_turrets(self, game_state):
        turret_locations = [[18, 10], [9, 10], [6, 12], [21, 12]] # Main center turrets
        secondary_locations = [[15, 8], [12, 8]] # Close center turrets
        if game_state.turn_number >= 1 and game_state.get_resource(SP, 0) >= 4:
            turret_locations.append([3, 12])
            turret_locations.append([24, 12])
        if game_state.turn_number >= 3 and game_state.get_resource(SP, 0) >= 8:
            turret_locations.append([9, 12])
            turret_locations.append([18, 12])
        if game_state.turn_number >= 5 and game_state.get_resource(SP, 0) >= 12:
            turret_locations.append([8, 10])
            turret_locations.append([19, 10])
            
        game_state.attempt_spawn(TURRET, turret_locations)

        if game_state.get_resource(SP, 0) >= 4 and game_state.turn_number >= 3:
            game_state.attempt_spawn(TURRET, secondary_locations)

        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number >= 8:
            game_state.attempt_upgrade(turret_locations)

    def place_supports(self, game_state):
        support_locations = []
        if game_state.turn_number >= 4:
            support_locations.append([18, 9])
            support_locations.append([9, 9])
        if game_state.turn_number >= 6:
            support_locations.append([17, 9])
            support_locations.append([10, 9])
        if game_state.turn_number >= 12:
            support_locations.append([11, 8])
            support_locations.append([16, 8])

        game_state.attempt_spawn(SUPPORT, support_locations)

        if game_state.get_resource(SP, 0) > 16 and game_state.turn_number >= 10:
            game_state.attempt_upgrade(support_locations)

    def spawn_interceptors(self, game_state):
        num_interceptors = self.get_interceptor_num(game_state)
        interceptor_locations = [[1, 12], [26, 12]]
        if game_state.turn_number != 0:
            possible_locations_L = [[2, 11], [3, 10], [4, 9], [5, 8]]
            possible_locations_R = [[25, 11], [24, 10], [23, 9], [22, 8]]

            left = self.least_damage_interceptor_spawn(game_state, possible_locations_L)
            right = self.least_damage_interceptor_spawn(game_state, possible_locations_R)
            
            interceptor_locations = [left, right]
        for _ in range(num_interceptors):
            game_state.attempt_spawn(INTERCEPTOR, interceptor_locations)

    def least_damage_interceptor_spawn(self, game_state, location_options):
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path[:10]:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        for dmg in damages:
            if dmg < 10:
                return location_options[damages.index(dmg)]
        return location_options[damages.index(min(damages))]

    # Returns the spawn point that will receive the least damage and the damage at that point
    def least_damage_spawn(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)

        damages = []
        # Get the damage estimate each path will take
        for location in deploy_locations:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path[8:]: # Ignore first 8 path locations
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return deploy_locations[damages.index(min(damages))], min(damages)

    def wall_blocking_path(self, game_state, spawn_location):
        path = game_state.find_path_to_edge(spawn_location)

        enemy_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)

        end_location = path[len(path)-1]

        return not (end_location in enemy_edges), end_location

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def get_interceptor_num(self, game_state):
        if game_state.get_resource(MP, 1) < 13 or game_state.turn_number < 15:
            return 1
        elif game_state.turn_number > 30 and game_state.get_resource(MP, 1) > 15: # never happens
            return 3
        return 2

    def scout_spam(self, game_state, location):
        scout_count = self.get_scout_count(game_state)
        if scout_count <= 4: return

        for _ in range(scout_count):
            game_state.attempt_spawn(SCOUT, location)

    def get_scout_count(self, game_state):
        return trunc(game_state.get_resource(MP, 0))

    def demolisher_spam(self, game_state, location):
        demolisher_count = self.get_demolisher_count(game_state)
        if demolisher_count <= 3: return

        for _ in range(demolisher_count):
            game_state.attempt_spawn(DEMOLISHER, location)

    def get_demolisher_count(self, game_state):
        return trunc(game_state.get_resource(MP, 0) / 3)

    def spawn_infiltrator_scouts(self, game_state, side):
        if game_state.get_resource(MP, 0) < 13: return

        suicide_scout_location = []
        suicide_scout_num = 7

        attacker_scout_location = []
        attacker_scout_num = trunc(game_state.get_resource(MP, 0) - suicide_scout_num)

        if side == game_state.game_map.BOTTOM_LEFT:
            suicide_scout_location = [20, 6]
            attacker_scout_location = [15, 1]
        else:
            suicide_scout_location = [7, 6]
            attacker_scout_location = [12, 1]

        for _ in range(suicide_scout_num):
            game_state.attempt_spawn(SCOUT, suicide_scout_location)
        for _ in range(attacker_scout_num):
            game_state.attempt_spawn(SCOUT, attacker_scout_location)

    def get_location_side(self, game_state, location):
        if location[0] < 14:
            return game_state.game_map.TOP_LEFT
        return game_state.game_map.TOP_RIGHT

    def place_infiltrator_counter_walls(self, game_state, side):
        wall_locations = []

        if side == game_state.game_map.BOTTOM_LEFT:
            wall_locations = [[16, 2], [15, 2], [14, 2], [13, 2], [12, 3], [11, 4], [10, 5], [9, 6], [8, 7], [7, 8]]
        elif side == game_state.game_map.BOTTOM_RIGHT:
            wall_locations = [[11, 2], [12, 2], [13, 2], [14, 2], [15, 3], [16, 4], [17, 5], [18, 6], [19, 7], [20, 8]]

        game_state.attempt_spawn(WALL, wall_locations)

    def clear_infiltrator_counter_walls(self, game_state, side):
        wall_locations = []

        if side == game_state.game_map.BOTTOM_LEFT:
            wall_locations = [[16, 2], [15, 2], [12, 3], [11, 4], [10, 5], [9, 6], [8, 7], [7, 8]]
        elif side == game_state.game_map.BOTTOM_RIGHT:
            wall_locations = [[11, 2], [12, 2], [15, 3], [16, 4], [17, 5], [18, 6], [19, 7], [20, 8]]

        game_state.attempt_remove(wall_locations)

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

        if self.last_enemy_spawn_update != spawns:
            self.last_enemy_spawn_update = spawns

            for spawn in spawns:
                if spawn[1] == 0:
                    self.hypothetical_state.game_map.add_unit(WALL, spawn[0], spawn[3]-1)
                elif spawn[1] == 1:
                    self.hypothetical_state.game_map.add_unit(SUPPORT, spawn[0], spawn[3]-1)
                elif spawn[1] == 2:
                    self.hypothetical_state.game_map.add_unit(TURRET, spawn[0], spawn[3]-1)

            safest_spawn, least_damage = self.least_damage_spawn(self.hypothetical_state)
            path_blocked, end_location = self.wall_blocking_path(self.hypothetical_state, safest_spawn)

            gamelib.debug_write('END LOCATION IS ' + str(end_location), path_blocked)

            if path_blocked:
                gamelib.debug_write('USING INFILTRATOR COUNTER STRAT')
                self.counter_infiltrator_strat = True

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
