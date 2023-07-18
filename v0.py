import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from math import *

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

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
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        Start by placing wall funnel and turrets. Also infiltrators at ends of wall
        """
        # First, place basic defenses
        self.base_funnel(game_state)

        # Look for open spot. If open spot found, spam scouts. If not, place demolishers
        safest_spawn, least_damage = self.least_damage_spawn(game_state)
        if self.should_spawn_scouts(game_state, least_damage):
            gamelib.debug_write('spawning scouts...')
            self.scout_spam(game_state, safest_spawn)
        else:
            self.demolisher_spam(game_state, safest_spawn)

    def should_spawn_scouts(self, game_state, damage_taken):
        if damage_taken == 0: return True

        num_scouts = self.get_scout_count(game_state)

        return ((num_scouts * 15) / damage_taken) >= 2.8

    # Base defense of turrets, walls, interceptors, and supports
    def base_funnel(self, game_state):
        projected_SP = game_state.get_resource(SP, 0)

        # Infiltrator walls
        # if enemy scores there:
        # TODO TODO TODO KSJDKFJ
        """
        YOU NEED TO DO THIS: CHECK WHERE ENEMY SCORES OR WHERE ENEMY ATTEMPTS TO SCORE 
        (AND SELF DESTRUCTS) YOU KNOW WHAT SIDE TO PLACE WALLS ON IF THAT HAPPENS
        """
        left_side = [[0, 13], [1, 12], [2, 11], [3, 10]]
        right_side = [[27, 13], [26, 12], [25, 11], [24, 10]]

        gamelib.debug_write('checking')
        if any(location in self.scored_on_locations for location in left_side):
            self.place_infiltrator_walls(game_state, 'left')
        if any(location in self.scored_on_locations for location in right_side):
            self.place_infiltrator_walls(game_state, 'right')

        # Base wall
        self.place_base_walls(game_state)

        # Turrets
        self.place_turrets(game_state)

        # Extra funnel walls
        wall_locations = [[10, 10], [17, 10], [11, 9], [16, 9]]
        game_state.attempt_spawn(WALL, wall_locations)

        # Supports
        if game_state.get_resource(SP, 0) > 20:
            self.place_supports(game_state)

        # Center turret walls
        if game_state.turn_number >= 10 and game_state.get_resource(SP, 0) > 20:
            self.place_L_walls(game_state)

        # Interceptors
        if ((game_state.turn_number < 20 and game_state.get_resource(MP, 1) > 10) or game_state.turn_number < 2):
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
        turret_locations = [[18, 10], [9, 10]] # Main center turrets
        secondary_locations = [[15, 8], [12, 8]] # Close center turrets
        if game_state.turn_number >= 2 and game_state.get_resource(SP, 0) > 15:
            turret_locations.append([3, 12])
            turret_locations.append([24, 12])
        if game_state.turn_number >= 5 and game_state.get_resource(SP, 0) > 15:
            turret_locations.append([6, 12])
            turret_locations.append([21, 12])
            
        game_state.attempt_spawn(TURRET, turret_locations)
        game_state.attempt_upgrade(turret_locations)

        if game_state.get_resource(SP, 0) > 8 and game_state.turn_number > 10: 
            game_state.attempt_spawn(TURRET, secondary_locations)
        if game_state.get_resource(SP, 0) > 20 and game_state.turn_number > 30: 
            game_state.attempt_upgrade(secondary_locations)

    def place_supports(self, game_state):
        support_locations = []
        if game_state.turn_number >= 10:
            # Right behind turrets
            support_locations.append([18, 9])
            support_locations.append([9, 9])
        if game_state.turn_number >= 20:
            support_locations.append([17, 9])
            support_locations.append([10, 9])

        game_state.attempt_spawn(SUPPORT, support_locations)
        game_state.attempt_upgrade(support_locations)

    def place_L_walls(self, game_state):
        wall_locations_L = [[10, 10], [10, 11], [9, 11], [8, 11]]
        wall_locations_R = [[17, 10], [17, 11], [18, 11], [19, 11]]

        game_state.attempt_spawn(WALL, wall_locations_L + wall_locations_R) 
        game_state.attempt_upgrade(wall_locations_L + wall_locations_R)

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
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
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
        demolisher_count = trunc(game_state.get_resource(MP, 0) / 3)
        if demolisher_count <= 3: return

        for _ in range(demolisher_count):
            game_state.attempt_spawn(DEMOLISHER, location)

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
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
