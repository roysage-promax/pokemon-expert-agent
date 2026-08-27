from poke_env.battle import AbstractBattle, MoveCategory
from poke_env.player import Player

# ==================================================
# Tunable values. Change these, re-run, compare.
# Everything the agent decides with lives here.
# ==================================================

""" ---- General ---- """
# Assumed incoming damage (fraction of our max HP) when the opponent has not
# revealed any attacking move yet.
DEFAULT_INCOMING_DAMAGE = 0.35

# A voluntary switch gives the opponent a free turn, so it has to beat the
# best move by this much before we take it.
SWITCH_MARGIN = 1000.0

# How much spare HP above the incoming damage counts as a fully safe turn.
SAFE_TURN_SPREAD = 0.5

# EV points we assume a hidden opponent has put into a stat (0 to 252).
OPPONENT_EV_ASSUMPTION = 0

""" ---- Damaging moves ---- """
DAMAGE_SCALE = 100.0        # Highest score a damaging move can approach.
DAMAGE_SATURATION = 200.0
STAT_RATIO_MIN = 0.25
STAT_RATIO_MAX = 2.0
PRIORITY_WEIGHT = 0.0
REVENGE_HP = 0.4
REVENGE_BONUS = 10.0
RECOIL_WEIGHT = 40.0

# Score for a move the opponent is immune to. _best_move also starts from this,
# so that an all-immune moveset picks nothing and we switch instead.
IMMUNE_SCORE = -1000.0

""" ---- Recover ---- """
RECOVER_WEIGHT = 90.0
RECOVER_HP_CAP = 0.9
RECOVER_FULL_NEED = 0.5     # Missing HP that scores the full weight.

""" ---- Setup moves ---- """
SWORDS_DANCE_WEIGHT = 80.0
CALM_MIND_WEIGHT = 80.0
AGILITY_WEIGHT = 75.0
AGILITY_SLOWER_NEED = 1.0   # Need when we are the slower Pokemon.
AGILITY_FASTER_NEED = 0.25

""" ---- Thunder Wave ---- """
THUNDER_WAVE_WEIGHT = 75.0
THUNDER_WAVE_SLOWER_NEED = 1.0
THUNDER_WAVE_FASTER_NEED = 0.5

""" ---- Spikes ---- """
SPIKES_WEIGHT = 75.0
SPIKES_BENCH_DIVISOR = 3.0  # Bench size that scores the full weight.
SPIKES_LAYER_VALUE = {      # Value of adding a layer on top of this many.
    0: 1.0,
    1: 0.7,
    2: 0.4,
}

""" ---- Taunt ---- """
TAUNT_UNKNOWN_SCORE = 10.0
TAUNT_BASE = 20.0
TAUNT_PER_STATUS_MOVE = 20.0
TAUNT_CAP = 80.0
TAUNT_SLOWER_PENALTY = 0.6

# Any status move without its own rule above.
UNKNOWN_STATUS_SCORE = 0.0

""" ---- Tera ---- """
# Do not spend tera on a Pokemon below this much HP, it is about to faint.
TERA_MIN_HP = 0.5

""" ---- Switching ---- """
SWITCH_DEFENCE_WEIGHT = 45.0
SWITCH_OFFENCE_WEIGHT = 30.0
SWITCH_HEALTH_WEIGHT = 25.0

# Type chart breakpoints used to bucket a damage multiplier.
RESIST_CUTOFF = 0.5
NEUTRAL_CUTOFF = 1.0
SUPER_CUTOFF = 2.0

# How good it is to take the opponent's best type at each breakpoint.
SWITCH_DEFENCE_RESIST = 1.0
SWITCH_DEFENCE_NEUTRAL = 0.6
SWITCH_DEFENCE_WEAK = 0.2
SWITCH_DEFENCE_VERY_WEAK = 0.0

# How good it is to hit the opponent with our own types.
SWITCH_OFFENCE_SUPER = 1.0
SWITCH_OFFENCE_NEUTRAL = 0.6
SWITCH_OFFENCE_RESISTED = 0.2

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
            if candidate is None:
                return self.choose_random_move(battle)
            return self.create_order(candidate)

        # It's not a forced switch, find the next best move to use
        best_move, best_score = self._best_move(battle)
        best_switch, switch_score = self._best_switch(battle)

        # Attack by default. Only switch when it is clearly better.
        if best_move is not None and switch_score <= best_score + SWITCH_MARGIN:
            if self._should_tera(battle, best_move):
                return self.create_order(best_move, terastallize=True)
            return self.create_order(best_move)

        if best_switch is not None:
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

        # Estimate at level 100 with 31 IVs and a neutral nature.
        if value is None:
            evs = OPPONENT_EV_ASSUMPTION / 4
            if stat == "hp":
                value = 2 * pokemon.base_stats["hp"] + evs + 141
            else:
                value = 2 * pokemon.base_stats[stat] + evs + 36

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
            return IMMUNE_SCORE

        accuracy = move.accuracy

        if move.category.name == "PHYSICAL":
            stat_ratio = self._stat(me, "atk", True) / max(1.0, self._stat(opp, "def", False))
        else:
            stat_ratio = self._stat(me, "spa", True) / max(1.0, self._stat(opp, "spd", False))
        stat_ratio = max(STAT_RATIO_MIN, min(STAT_RATIO_MAX, stat_ratio))

        priority_score = 0.0
        if move.priority > 0:
            priority_score = PRIORITY_WEIGHT * move.priority

            if opp.current_hp_fraction < REVENGE_HP:
                priority_score += REVENGE_BONUS

        recoil_score = RECOIL_WEIGHT * (move.recoil or 0.0)

        raw = power * stab * effectiveness * accuracy * stat_ratio
        score = DAMAGE_SCALE * raw / (raw + DAMAGE_SATURATION)
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
        safe_turn = max(
            0.0,
            min(1.0, (hp_ratio - incoming_damage_ratio) / SAFE_TURN_SPREAD),
        )
        
        my_speed = float(me.base_stats["spe"])
        opp_speed = float(opp.base_stats["spe"])
        
        # --------------------------------------------------
        # 1. Recovery
        # --------------------------------------------------
        if (move_id == "recover"):
            if hp_ratio > RECOVER_HP_CAP: # Dont heal if high health
                return 0.0

            if incoming_damage_ratio > hp_ratio:    # If opponent is going to KO you, don't waste heal.
                return 0.0

            # Score reaches maximum when RECOVER_FULL_NEED of our HP is missing.
            missing_hp = 1.0 - hp_ratio
            healing_need = min(1.0, missing_hp / RECOVER_FULL_NEED)
            return RECOVER_WEIGHT * healing_need
        
        # --------------------------------------------------
        # 2. Stat change
        # --------------------------------------------------
        if move_id == "swordsdance":

            attack_stage = me.boosts.get("atk", 0)

            if attack_stage >= 6:
                return 0.0

            boost_need = (6.0 - attack_stage) / 6.0

            score = SWORDS_DANCE_WEIGHT * boost_need * safe_turn

            return score

        if move_id == "calmmind":

            special_attack_stage = me.boosts.get("spa", 0)
            special_defense_stage = me.boosts.get("spd", 0)

            if special_attack_stage >= 6 and special_defense_stage >= 6:
                return 0.0

            spa_need = (6.0 - special_attack_stage) / 6.0
            spd_need = (6.0 - special_defense_stage) / 6.0

            boost_need = (spa_need + spd_need) / 2.0

            score = CALM_MIND_WEIGHT * boost_need * safe_turn

            return score

        if move_id == "agility":

            speed_stage = me.boosts.get("spe", 0)

            if speed_stage >= 6:
                return 0.0

            # Agility is most useful when we are currently slower.
            if my_speed < opp_speed:
                speed_need = AGILITY_SLOWER_NEED
            else:
                speed_need = AGILITY_FASTER_NEED

            score = AGILITY_WEIGHT * speed_need * safe_turn

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
                speed_need = THUNDER_WAVE_SLOWER_NEED
            else:
                speed_need = THUNDER_WAVE_FASTER_NEED

            score = THUNDER_WAVE_WEIGHT * speed_need * move.accuracy

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
            switch_value = min(1.0, opponents_on_bench / SPIKES_BENCH_DIVISOR)

            # Each additional layer is given a lower score.
            layer_value = SPIKES_LAYER_VALUE[spikes_layers]

            score = SPIKES_WEIGHT * switch_value * layer_value

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
                score = TAUNT_UNKNOWN_SCORE
            else:
                score = min(
                    TAUNT_CAP,
                    TAUNT_BASE + TAUNT_PER_STATUS_MOVE * number_of_status_moves
                )

            # Taunt is more useful when we act first.
            if my_speed < opp_speed:
                score *= TAUNT_SLOWER_PENALTY

            return score

        return UNKNOWN_STATUS_SCORE
        
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
        best_score = IMMUNE_SCORE

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
        # --------------------------------------------------
        # 1. Defence: how hard the opponent's types hit this candidate.
        # --------------------------------------------------
        worst = 0.0
        for opponent_type in opp.types:
            if opponent_type is not None:
                worst = max(worst, candidate.damage_multiplier(opponent_type))

        if worst <= RESIST_CUTOFF:
            defence = SWITCH_DEFENCE_RESIST
        elif worst <= NEUTRAL_CUTOFF:
            defence = SWITCH_DEFENCE_NEUTRAL
        elif worst <= SUPER_CUTOFF:
            defence = SWITCH_DEFENCE_WEAK
        else:
            defence = SWITCH_DEFENCE_VERY_WEAK

        # --------------------------------------------------
        # 2. Offence: how hard this candidate's own types hit the opponent.
        # --------------------------------------------------
        best = 0.0
        for my_type in candidate.types:
            if my_type is not None:
                best = max(best, opp.damage_multiplier(my_type))

        if best >= SUPER_CUTOFF:
            offence = SWITCH_OFFENCE_SUPER
        elif best >= NEUTRAL_CUTOFF:
            offence = SWITCH_OFFENCE_NEUTRAL
        else:
            offence = SWITCH_OFFENCE_RESISTED

        # --------------------------------------------------
        # 3. Health
        # --------------------------------------------------
        health = candidate.current_hp_fraction

        return (
            SWITCH_DEFENCE_WEIGHT * defence
            + SWITCH_OFFENCE_WEIGHT * offence
            + SWITCH_HEALTH_WEIGHT * health
        )

    def _best_switch(self, battle):
        """
        Score every pokemon in battle.available_switches and return
        the best candidate to switch in.

        input: current battle state
        output: pokemon, score
        """
        opp = battle.opponent_active_pokemon

        best_switch = None
        best_score = float("-inf")

        for candidate in battle.available_switches:
            score = self._score_switch(candidate, opp, battle)

            if score > best_score:
                best_score = score
                best_switch = candidate

        return best_switch, best_score

    def _best_forced_switch(self, battle):
        """
        Select legal replacement when it's forced switch.

        input: current battle state
        output: pokemon
        """
        best_switch, _ = self._best_switch(battle)

        return best_switch

    """ ----------------Special Decisions---------------- """
    def _tera_type(self, battle, me):
        """
        Our tera types are only in the team preview data, not on the active
        Pokemon, so look ours up by species.

        input: current battle state, our active pokemon
        output: pokemon type, or None if we cannot find it
        """
        for pokemon in battle.teampreview_team:
            if pokemon.species == me.species:
                return pokemon.tera_type

        return None

    def _should_tera(self, battle, move):
        """
        Decide if we should spend tera

        input: current battle state, the move we are about to use
        outputs true or false
        """
        me = battle.active_pokemon
        opp = battle.opponent_active_pokemon

        if not battle.can_tera:
            return False

        tera_type = self._tera_type(battle, me)
        if tera_type is None:
            return False

        # Tera does nothing for a status move.
        if move.category.name == "STATUS":
            return False

        # Only worth it when the move gains STAB from our tera type.
        if move.type != tera_type:
            return False

        # Do not spend it on a move the opponent resists anyway.
        if opp.damage_multiplier(move) < NEUTRAL_CUTOFF:
            return False

        # Only when we are healthy enough to use the boost.
        return me.current_hp_fraction >= TERA_MIN_HP


    def teampreview(self, battle: AbstractBattle):
        """
        SET THE TEAM ORDER HERE
        """
        return "/team 1"
