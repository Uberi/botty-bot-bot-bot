#!/usr/bin/env python3

import re, json, time, random
from math import floor, ceil
from collections import namedtuple

from .utilities import BasePlugin
from .utilities import untag_word

class AgarioPlugin(BasePlugin):
    """
    1D agar.io game plugin for Botty.
    """
    def __init__(self, bot):
        super().__init__(bot)

        self.last_step_time = 0
        self.player_locations = {}
        self.player_movement = {}
        self.player_index = {}
        self.player_split_cooldown = {}
        self.game_map = []
        self.game_channel, self.game_thread = None, None

        self.map_size = 150
        self.empty = " "
        self.food = "\u25E6"

    def on_step(self):
        current_time = time.time()
        if current_time - self.last_step_time < 0.2: return False
        self.last_step_time = current_time

        if self.game_channel is None: return # no game going on

        self.step_game()

        return True

    def on_message(self, m):
        if not m.is_user_text_message: return False
        text = self.sendable_text_to_text(m.text)
        user_name = self.get_user_name_by_id(m.user_id)

        # game start command
        match = re.search(r"^\s*pls\s+agar\s+me((?:\s+\S+)*)\s*$", text, re.IGNORECASE)
        if match:
            players = {user_name}
            for i, player in enumerate(match.group(1).replace(",", " ").split()):
                player = player.strip(" \t,")
                player_id = self.get_user_id_by_name(player)
                if player_id is None:
                    self.respond_raw("who's this {} person".format(player))
                    return True
                players.add(self.get_user_name_by_id(player_id))
            players = list(players)
            random.shuffle(players)

            self.initialize_game(m.channel_id, m.thread_id, players)
            return True

        if self.game_channel is None: return False # no game going on
        if m.channel_id != self.game_channel: return False # message isn't in the right channel

        # game stop command
        match = re.search(r"\b(stop|end|terminate|off|disable)\b", text, re.IGNORECASE)
        if match:
            self.end_game()
            return True

        if user_name not in self.player_locations: return False # player isn't in the game

        # directional commands
        match = re.search(r"^\s*([<v>])\s*(-|/|)\s*$", text, re.IGNORECASE)
        if match:
            direction, action = match.groups()
            offset = {"<": -1, "v": 0, ">": 1}[direction]
            if action == "-": # fire some mass in the desired direction
                self.fire(user_name, offset * 2)
            elif action == "/":
                self.split(user_name, offset * 4)
            else:
                self.player_movement[user_name] = offset
            return True

        return False

    def end_game(self):
        self.game_channel, self.game_thread = None, None
        masses = sorted(
            (
                (player, sum(location[1] for location in locations))
                for player, locations in self.player_locations.items()
            ),
            key = lambda pair: -pair[1]
        )

        self.respond(
            "*{} wins!*\n"
            "{}".format(
                untag_word(masses[0][0]),
                "\n".join(
                    "> *{}* has total mass {}".format(untag_word(player), total_mass)
                    for player, total_mass in masses
                )
            )
        )

    def initialize_game(self, channel, thread, players):
        self.game_channel, self.game_thread = channel, thread
        self.player_locations = {}
        self.player_movement = {}
        self.player_index = {}
        self.player_split_cooldown = {}
        current_position = random.randrange(0, 8)
        for i, player in enumerate(players):
            self.player_locations[player] = [[current_position, 1]]
            self.player_movement[player] = 0
            self.player_index[player] = i
            self.player_split_cooldown[player] = 0
            current_position = (current_position + random.randrange(10, 30)) % self.map_size
        self.game_map = [self.food if random.random() < 0.3 else self.empty for i in range(self.map_size)]

        self.say(
            "*AGAR.IO GAME STARTED* (players from left to right: {})\nSTARTING MAP: `{}`".format(
                ", ".join(players), self.render_map()
            ),
            channel_id=channel, thread_id=thread
        )

    def step_game(self):
        # occasionally spawn food in random places
        if random.random() < 0.3:
            self.game_map[random.randrange(self.map_size)] = self.food

        # apply joining after splitting
        for player, locations in self.player_locations.items():
            if self.player_split_cooldown[player] <= 0 and len(locations) > 1:
                locations = sorted(locations, key=lambda pair: pair[1])
                new_locations = []
                for i in range(0, len(locations) - 1, 2):
                    (position1, size1), (position2, size2) = locations[i], locations[i + 1]
                    new_locations.append([position1 if size1 > size2 else position2, size1 + size2])
                self.player_locations[player] = new_locations
                self.player_split_cooldown[player] = 20
            self.player_split_cooldown[player] -= 1

        # apply movement
        for player, movement in self.player_movement.items():
            for blob, (position, size) in enumerate(self.player_locations[player]):
                self.player_locations[player][blob][0] = (position + movement / size) % self.map_size

        # apply food eating
        for player, locations in self.player_locations.items():
            for blob, (position, size) in enumerate(locations):
                for i in range(ceil(position - size), floor(position + size + 1)):
                    if self.game_map[i % self.map_size] == self.food:
                        self.game_map[i % self.map_size] = self.empty
                        self.player_locations[player][blob][1] += 0.25

        # apply blobs from different players eating each other
        pairs = list(self.player_locations.items())
        for i, (player1, locations1) in enumerate(pairs):
            for blob1, location1 in enumerate(locations1):
                if location1 is None: continue
                position1, size1 = location1
                for player2, locations2 in pairs[i + 1:]:
                    for blob2, location2 in enumerate(locations2):
                        if location2 is None: continue
                        position2, size2 = location2
                        if (
                            position1 - size1 <= position2 <= position1 + size1 or
                            position2 - size2 <= position1 <= position2 + size2
                        ): # one blob is halfway or more inside of another blob, so it is being eaten
                            if size1 < size2 * 0.8: # blob 1 can be eaten by blob 2
                                self.player_locations[player2][blob2][1] += size1
                                self.player_locations[player1][blob1] = None
                            elif size2 < size1 * 0.8: # blob 2 can be eaten by blob 1
                                self.player_locations[player1][blob1][1] += size2
                                self.player_locations[player2][blob2] = None

        # remove dead player blobs
        new_player_locations = {}
        for player, locations in self.player_locations.items():
            new_locations = [location for location in locations if location is not None]
            if len(new_locations) > 0:
                new_player_locations[player] = new_locations
            else:
                del self.player_index[player]
                del self.player_movement[player]
        self.player_locations = new_player_locations
        if len(new_player_locations) < 2: # last player standing, player wins
            self.end_game()
            return

        # apply collision among blobs of a single player
        for player, locations in self.player_locations.items():
            for blob1, (position1, size1) in enumerate(locations):
                for blob2, (position2, size2) in enumerate(locations):
                    if blob1 == blob2: continue
                    if (
                        position1 - size1 <= position2 + size2 and
                        position2 - size2 <= position1 + size1
                    ): # a blob is colliding with another blob in the same player, nudge it out of the way
                        amount = min((position2 + size2) - (position1 - size1), (position1 + size1) - (position2 - size2))
                        if size1 < size2:
                            self.player_locations[player][blob1][0] = (position1 - amount) % self.map_size
                        else:
                            self.player_locations[player][blob2][0] = (position2 + amount) % self.map_size

        self.say("`{}`".format(self.render_map()), channel_id=self.game_channel, thread_id=self.game_thread)

    def fire(self, player, offset):
        locations = self.player_locations[player]
        location = max(locations, key=lambda location: location[1])
        if location[1] < 2: return # too small to fire
        if offset < 0: offset -= location[1]
        else: offset += location[1]
        location[1] -= 0.25
        self.game_map[round(location[0] + offset) % self.map_size] = self.food

    def split(self, player, offset):
        locations = self.player_locations[player]
        new_locations = []
        for i, location in enumerate(locations):
            if location[1] >= 2: # splitting is possible
                new_size = location[1] / 2
                locations[i][1] = new_size
                if offset < 0: actual_offset = offset - location[1]
                else: actual_offset = offset + location[1]
                new_locations.append([(location[0] + actual_offset) % self.map_size, new_size])
        self.player_locations[player] += new_locations
        self.player_split_cooldown[player] = 20

    def render_map(self):
        result = list(self.game_map)
        for player, locations in self.player_locations.items():
            for position, size in locations:
                result[round(position - size) % self.map_size] = "("
                result[round(position) % self.map_size] = str(self.player_index[player] + 1)
                result[round(position + size) % self.map_size] = ")"
        return "".join(result)
