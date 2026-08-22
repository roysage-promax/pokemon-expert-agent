from poke_env.battle import AbstractBattle, MoveCategory
from poke_env.player import Player

# Assumed incoming damage (fraction of our max HP) when the opponent has not
# revealed any attacking move yet.
DEFAULT_INCOMING_DAMAGE = 0.35

"""
Define your team here. You can use the team builder on https://play.pokemonshowdown.com/teambuilder 

Create a team and then copy the text here. 

Make sure to keep the triple quotes around the team text.

Make sure to use the Uber Format
"""

team = """
Deoxys-Speed @ Focus Sash
Ability: Pressure
Tera Type: Ghost
EVs: 248 HP / 8 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunder Wave
- Spikes
- Taunt
- Psycho Boost

Kingambit @ Dread Plate
Ability: Supreme Overlord
Tera Type: Dark
EVs: 56 HP / 252 Atk / 200 Spe
Adamant Nature
- Swords Dance
- Kowtow Cleave
- Iron Head
- Sucker Punch

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Swords Dance
- Behemoth Blade
- Close Combat
- Wild Charge

Arceus-Fairy @ Pixie Plate
Ability: Multitype
Tera Type: Fire
EVs: 248 HP / 72 Def / 188 Spe
Bold Nature
IVs: 0 Atk
- Calm Mind
- Judgment
- Taunt
- Recover

Eternatus @ Power Herb
Ability: Pressure
Tera Type: Fire
EVs: 124 HP / 252 SpA / 132 Spe
Modest Nature
IVs: 0 Atk
- Agility
- Meteor Beam
- Dynamax Cannon
- Fire Blast

Koraidon @ Life Orb
Ability: Orichalcum Pulse
Tera Type: Fire
EVs: 8 HP / 248 Atk / 252 Spe
Jolly Nature
- Swords Dance
- Scale Shot
- Flame Charge
- Close Combat
"""


class CustomAgent(Player):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, team=team, **kwargs)

    def choose_move(self, battle: AbstractBattle):
        """
        DO NOT EDIT THIS FUNCTION.
        """
        me = battle.active_pokemon
        opp = battle.opponent_active_pokemon

        if me is None or opp is None:
            return self.choose_random_move(battle)

        return self._choose_move(battle)

    def _choose_move(self, battle: AbstractBattle):
        """
        DO EDIT THIS FUNCTION
        
        It's like a controller. I should write which moves,
        otherwise it will select a random move for me.
        """
        
        if battle.force_switch:
            candidate = self._best_forced_switch(battle)
            return self.create_order(candidate)
        
        # It's not a forced switch, find the next best move to use
        best_move, best_score = self._best_move(battle)
        best_switch, switch_score = self._best_switch(battle)
        
        # If move higher than switch, use move.
        if (best_move is not None and best_score >= switch_score):
            return self.create_order(best_move)
        
        # If switch higher than move, use switch.
        if (best_switch is not None and switch_score > best_score):
            return self.create_order(best_switch)
        
        # Controller basically failed, return random move.
        print("Controller failed, returning random move!")
        return self.choose_random_move(battle)
    
    """ ----------------Stat evaluation---------------- """
    def _stat(self, pokemon, stat, is_mine):
        """
        Returns a usable stat value. Opponent's stats are guessed.
        
        input: pokemon, stat name, mine or opponent's
        output: stat value (float)
        """
        value = None

        # Our own real stats are known. The opponent's are always hidden.
        if is_mine and pokemon.stats:
            value = pokemon.stats.get(stat)

        # Estimate at level 100 with 31 IVs, no EVs and a neutral nature.
        if value is None:
            if stat == "hp":
                value = 2 * pokemon.base_stats["hp"] + 141
            else:
                value = 2 * pokemon.base_stats[stat] + 36

        # Stat stages are multipliers, from -6 to +6.
        stage = pokemon.boosts.get(stat, 0)
        if stage > 0:
            value = value * (2 + stage) / 2
        else:
            value = value * 2 / (2 - stage)

        return max(1.0, float(value))
    
    """ ----------------Move evaluation---------------- """
    def _score_damaging_move(self, move, me, opp):
        """
        Score an attacking move using power, STAB, effectiveness,
        accuracy, stats, priority, recoil, and knockout potential.
        
        input: move, active pokemon, opponent
        output: score (float)
        """
        power = move.base_power * move.expected_hits
        
        if move.type in me.types:
            stab = 1.5
        else:
            stab = 1.0
        
        effectiveness = opp.damage_multiplier(move)
        if effectiveness == 0:
            return -1000.0
        
        accuracy = move.accuracy
        
        if move.category.name == "PHYSICAL":
            stat_ratio = self._stat(me, "atk", True) / max(1.0, self._stat(opp, "def", False))
        else:
            stat_ratio = self._stat(me, "spa", True) / max(1.0, self._stat(opp, "spd", False))
        stat_ratio = max(0.5, min(2.0, stat_ratio)) # Clamp stat ratio to [0.5, 2.0]

        priority_score = 0.0
        if move.priority > 0:
            priority_score = 5.0 * move.priority

            if opp.current_hp_fraction < 0.40:
                priority_score += 10.0

        recoil_score = 40.0 * (move.recoil or 0.0)
        
        raw = power * stab * effectiveness * accuracy * stat_ratio
        score = 100.0 * raw / (raw + 300.0)
        score = score + priority_score - recoil_score
        
        return score
        
    def _score_status_move(self, move, battle, me, opp):
        """
        Score moves such as Swords, Dance, Recover, Taunt,
        Thunder wave, and spikes.
        
        input: move, current battle state
        output score (float)
        """
        
        move_id = move.id
        hp_ratio = me.current_hp_fraction

        # TODO: estimate this from the opponent's revealed moves instead of
        # assuming a fixed value. poke-env does not provide it.
        incoming_damage_ratio = DEFAULT_INCOMING_DAMAGE

        # 1 means very safe. 0 means the opponent is expected to KO you.
        safe_turn = max(0.0, min(1.0, (hp_ratio - incoming_damage_ratio) / 0.5))
        
        my_speed = float(me.base_stats["spe"])
        opp_speed = float(opp.base_stats["spe"])
        
        # --------------------------------------------------
        # 1. Recovery
        # --------------------------------------------------
        if (move_id == "recover"):
            if hp_ratio > 0.90: # Dont heal if high health
                return 0.0
            
            if incoming_damage_ratio > hp_ratio:    # If opponent is going to KO you, don't waste heal.
                return 0.0
            
            # Score reaches maximum when at least 50% HP is missing.
            missing_hp = 1.0 - hp_ratio
            healing_need = min(1.0, missing_hp / 0.5)
            return 90.0 * healing_need
        
        # --------------------------------------------------
        # 2. Stat change
        # --------------------------------------------------
        if move_id == "swordsdance":

            attack_stage = me.boosts.get("atk", 0)

            if attack_stage >= 6:
                return 0.0

            boost_need = (6.0 - attack_stage) / 6.0

            score = 80.0 * boost_need * safe_turn

            return score

        if move_id == "calmmind":

            special_attack_stage = me.boosts.get("spa", 0)
            special_defense_stage = me.boosts.get("spd", 0)

            if special_attack_stage >= 6 and special_defense_stage >= 6:
                return 0.0

            spa_need = (6.0 - special_attack_stage) / 6.0
            spd_need = (6.0 - special_defense_stage) / 6.0

            boost_need = (spa_need + spd_need) / 2.0

            score = 80.0 * boost_need * safe_turn

            return score

        if move_id == "agility":

            speed_stage = me.boosts.get("spe", 0)

            if speed_stage >= 6:
                return 0.0

            # Agility is most useful when we are currently slower.
            if my_speed < opp_speed:
                speed_need = 1.0
            else:
                speed_need = 0.25

            score = 75.0 * speed_need * safe_turn

            return score
        
        # --------------------------------------------------
        # 3. Status Ailment
        # --------------------------------------------------
        if (move_id == "thunderwave"):
            # Do not use it if the opponent already has a status.
            if opp.status is not None:
                return 0.0

            opponent_types = [
                pokemon_type.name
                for pokemon_type in opp.types
                if pokemon_type is not None
            ]

            # Thunder Wave normally fails against these types.
            if "ELECTRIC" in opponent_types or "GROUND" in opponent_types:
                return 0.0

            # Paralysis is more valuable against a faster opponent.
            if opp_speed > my_speed:
                speed_need = 1.0
            else:
                speed_need = 0.5

            # 0.9 represents Thunder Wave's 90% accuracy.
            score = 75.0 * speed_need * 0.9

            return score
        
        # --------------------------------------------------
        # 4. Field & Weather Effects
        # --------------------------------------------------
        if (move_id == "spikes"):
            spikes_layers = 0

            for condition, layers in battle.opponent_side_conditions.items():
                if condition.name == "SPIKES":
                    spikes_layers = layers

            if spikes_layers >= 3:
                return 0.0

            opponents_alive = sum(
                1
                for pokemon in battle.opponent_team.values()
                if not pokemon.fainted
            )

            opponents_on_bench = max(0, opponents_alive - 1)

            if opponents_on_bench == 0:
                return 0.0

            # More remaining opponents means more future switches.
            switch_value = min(1.0, opponents_on_bench / 3.0)

            # Each additional layer is given a lower score.
            layer_value = {
                0: 1.0,
                1: 0.7,
                2: 0.4,
            }[spikes_layers]

            score = 75.0 * switch_value * layer_value

            return score
        
        # --------------------------------------------------
        # 5. Utility and Control
        # --------------------------------------------------
        if (move_id == "taunt"):
            known_moves = list(opp.moves.values())

            number_of_status_moves = sum(
                1
                for known_move in known_moves
                if known_move.category.name == "STATUS"
            )

            # Give a small score because some moves may still be unknown.
            if number_of_status_moves == 0:
                score = 10.0
            else:
                score = min(
                    80.0,
                    20.0 + 20.0 * number_of_status_moves
                )

            # Taunt is more useful when we act first.
            if my_speed < opp_speed:
                score *= 0.6

            return score
            
        return 0.0
        
    def _best_move(self, battle):
        """
        Score every legal move in battle.available_moves and return
        the best one.
        
        input: current battle state
        output: move, score
        """
        
        me = battle.active_pokemon
        opp = battle.opponent_active_pokemon
        
        best_move = None
        best_score = -1000.0
        
        for move in battle.available_moves:
            if move.category.name == "STATUS":
                score = self._score_status_move(move, battle, me, opp)
            else:
                score = self._score_damaging_move(move, me, opp)
            
            if score > best_score:
                best_score = score
                best_move = move
                
        return best_move, best_score
        
    """ ----------------Switch evaluation---------------- """
    def _score_switch(self, candidate, opp, battle):
        """
        A score on how safe and useful if bringing this pokemon in.

        input: candidate pokemon, opponent pokemon, battle state
        output: score (float)
        """
    
    def _best_switch(self, battle):
        """
        Score every pokemon in battle.available_switches and return
        the best candidate to switch in.

        input: current battle state
        output: pokemon, score
        """
        # TEMPORARY: never switch voluntarily, so we can measure the
        # attacking logic on its own.
        return None, float("-inf")

    def _best_forced_switch(self, battle):
        """
        Select legal replacement when it's forced switch.

        input: current battle state
        output: pokemon
        """
        # TEMPORARY: send out the first healthy Pokemon available.
        if battle.available_switches:
            return battle.available_switches[0]

        return None

    """ ----------------Special Decisions---------------- """
    def _should_tera(self, battle, move):
        """ 
        Decide if we should spend tera
        
        outputs true or false
        """
    
    def teampreview(self, battle: AbstractBattle):
        """
        SET THE TEAM ORDER HERE
        """
        return "/team 1"
