import random
import json


class Effect:
    def __init__(self, name, duration, value=0):
        self.name = name
        self.duration = duration
        self.value = value

    def apply_effect(self, target):
        return ""

    def tick(self, target):
        self.duration -= 1
        return ""

    @property
    def is_expired(self):
        return self.duration <= 0


class PoisonEffect(Effect):
    def __init__(self, duration, damage_per_turn):
        super().__init__("Яд", duration, damage_per_turn)

    def apply_effect(self, target):
        return f"{target.name} отравлен!"

    def tick(self, target):
        super().tick(target)
        if target.is_alive:
            target.take_damage(self.value)
            return f"Яд наносит {self.value} урона"


class ShieldEffect(Effect):
    def __init__(self, duration, shield_strength):
        super().__init__("Щит", duration, shield_strength)
        self.remaining_shield = shield_strength

    def apply_effect(self, target):
        return f"{target.name} получает щит!"

    def absorb_damage(self, damage):
        if self.remaining_shield >= damage:
            self.remaining_shield -= damage
            return 0
        else:
            remaining_damage = damage - self.remaining_shield
            self.remaining_shield = 0
            return remaining_damage


class Human:
    def __init__(self, name, level=1):
        self._name = name
        self._level = level
        self._max_hp = 100
        self._hp = self._max_hp
        self._max_mp = 50
        self._mp = self._max_mp
        self._strength = 10
        self._agility = 10
        self._intelligence = 10
        self._effects = []
        self._inventory = []
        self.skills = []

    @property
    def name(self):
        return self._name

    @property
    def hp(self):
        return self._hp

    @property
    def max_hp(self):
        return self._max_hp

    @property
    def mp(self):
        return self._mp

    @property
    def strength(self):
        return self._strength

    @property
    def agility(self):
        return self._agility

    @property
    def intelligence(self):
        return self._intelligence

    @property
    def is_alive(self):
        return self._hp > 0

    @property
    def initiative(self):
        return self._agility + random.randint(1, 10)

    def take_damage(self, damage):
        if not self.is_alive:
            return f"{self.name} уже мертв!"

        for effect in self._effects:
            if isinstance(effect, ShieldEffect):
                damage = effect.absorb_damage(damage)
                if damage == 0:
                    return f"Щит поглотил урон!"

        self._hp = max(0, self._hp - damage)
        result = f"{self.name} получает {damage} урона. HP: {self._hp}"

        if not self.is_alive:
            result += f"\n{self.name} умер!"

        return result

    def attack(self, target):
        if not self.is_alive:
            return f"{self.name} не может атаковать!"

        damage = self._strength + random.randint(1, 5)
        if random.random() < 0.2:
            damage *= 2
            return f"КРИТ! {target.take_damage(damage)}"

        return target.take_damage(damage)

    def heal(self, amount):
        old_hp = self._hp
        self._hp = min(self._max_hp, self._hp + amount)
        return f"{self.name} лечит {self._hp - old_hp} HP"

    def restore_mp(self, amount):
        old_mp = self._mp
        self._mp = min(self._max_mp, self._mp + amount)
        return f"{self.name} восстанавливает {self._mp - old_mp} MP"

    def add_effect(self, effect):
        self._effects.append(effect)
        return effect.apply_effect(self)

    def process_effects(self):
        if not self._effects:
            return ""

        results = []
        expired_effects = []

        for effect in self._effects:
            result = effect.tick(self)
            if result:
                results.append(result)
            if effect.is_expired:
                expired_effects.append(effect)

        for effect in expired_effects:
            self._effects.remove(effect)

        return "\n".join(results)

    def add_item(self, item):
        self._inventory.append(item)

    def use_item(self, item_index, target=None):
        if not self.is_alive:
            return "Не может использовать предмет!"

        if item_index < 0 or item_index >= len(self._inventory):
            return "Нет такого предмета!"

        item = self._inventory.pop(item_index)
        if target is None:
            target = self

        return item.use(target)

    def __str__(self):
        return f"{self.name} - HP: {self._hp}/{self._max_hp}, MP: {self._mp}/{self._max_mp}"


class Skill:
    def __init__(self, name, mp_cost, damage_multiplier=1.0):
        self.name = name
        self.mp_cost = mp_cost
        self.damage_multiplier = damage_multiplier

    def can_use(self, user):
        return user.is_alive and user.mp >= self.mp_cost

    def use(self, user, targets):
        if not self.can_use(user):
            return "Не хватает MP!"

        user._mp -= self.mp_cost
        target = targets[0]

        if not target.is_alive:
            return "Цель мертва!"

        damage = int(user.strength * self.damage_multiplier + random.randint(1, 10))
        result = [f"{user.name} использует {self.name}!"]
        result.append(target.take_damage(damage))

        return "\n".join(result)


class HealSkill(Skill):
    def __init__(self, name, mp_cost, heal_multiplier=1.0):
        super().__init__(name, mp_cost)
        self.heal_multiplier = heal_multiplier

    def use(self, user, targets):
        if not self.can_use(user):
            return "Не хватает MP!"

        user._mp -= self.mp_cost
        target = targets[0] if targets else user

        if not target.is_alive:
            return "Нельзя лечить мертвого!"

        heal_amount = int(user.intelligence * self.heal_multiplier + random.randint(5, 15))
        return f"{user.name} использует {self.name}: {target.heal(heal_amount)}"


class PoisonSkill(Skill):
    def __init__(self, name, mp_cost, duration, damage_per_turn):
        super().__init__(name, mp_cost)
        self.duration = duration
        self.damage_per_turn = damage_per_turn

    def use(self, user, targets):
        if not self.can_use(user):
            return "Не хватает MP!"

        user._mp -= self.mp_cost
        target = targets[0]

        if not target.is_alive:
            return "Цель мертва!"

        poison_effect = PoisonEffect(self.duration, self.damage_per_turn)
        result = [f"{user.name} использует {self.name}!"]
        result.append(target.add_effect(poison_effect))

        return "\n".join(result)


class Item:
    def __init__(self, name):
        self.name = name

    def use(self, target):
        return f"Использован {self.name}"


class HealthPotion(Item):
    def __init__(self):
        super().__init__("Зелье здоровья")
        self.heal_amount = 50

    def use(self, target):
        if not target.is_alive:
            return "Нельзя использовать на мертвого!"
        return target.heal(self.heal_amount)


class ManaPotion(Item):
    def __init__(self):
        super().__init__("Зелье маны")
        self.mana_amount = 30

    def use(self, target):
        if not target.is_alive:
            return "Нельзя использовать на мертвого!"
        return target.restore_mp(self.mana_amount)


class Warrior(Human):
    def __init__(self, name, level=1):
        super().__init__(name, level)
        self._max_hp = 120 + level * 10
        self._hp = self._max_hp
        self._max_mp = 30 + level * 5
        self._mp = self._max_mp
        self._strength = 15 + level * 2
        self._agility = 8 + level
        self._intelligence = 5 + level

        self.skills = [
            Skill("Мощный удар", 10, 2.0),
            Skill("Вихрь", 15, 1.5)
        ]

        self.add_item(HealthPotion())
        self.add_item(HealthPotion())


class Mage(Human):
    def __init__(self, name, level=1):
        super().__init__(name, level)
        self._max_hp = 80 + level * 5
        self._hp = self._max_hp
        self._max_mp = 80 + level * 10
        self._mp = self._max_mp
        self._strength = 5 + level
        self._agility = 6 + level
        self._intelligence = 18 + level * 2

        self.skills = [
            Skill("Огненный шар", 12, 2.5),
            PoisonSkill("Яд", 15, 3, 10)
        ]

        self.add_item(ManaPotion())
        self.add_item(HealthPotion())


class Healer(Human):
    def __init__(self, name, level=1):
        super().__init__(name, level)
        self._max_hp = 90 + level * 6
        self._hp = self._max_hp
        self._max_mp = 70 + level * 8
        self._mp = self._max_mp
        self._strength = 6 + level
        self._agility = 7 + level
        self._intelligence = 16 + level * 2

        self.skills = [
            HealSkill("Лечение", 8, 1.5),
            HealSkill("Сильное лечение", 20, 2.0)
        ]

        self.add_item(HealthPotion())
        self.add_item(ManaPotion())


class Boss(Human):
    def __init__(self, name, level=5):
        super().__init__(name, level)
        self._max_hp = 300 + level * 50
        self._hp = self._max_hp
        self._max_mp = 100 + level * 20
        self._mp = self._max_mp
        self._strength = 20 + level * 3
        self._agility = 12 + level * 2
        self._intelligence = 15 + level * 2

        self.phase = 1

    def choose_action(self, enemies):
        alive_enemies = [e for e in enemies if e.is_alive]

        if not alive_enemies:
            return "Босс победил!"

        # Смена фаз
        if self.hp < self.max_hp * 0.3:
            self.phase = 3
        elif self.hp < self.max_hp * 0.6:
            self.phase = 2
        else:
            self.phase = 1

        if self.phase == 1:
            target = random.choice(alive_enemies)
            return self.attack(target)

        elif self.phase == 2:
            if self._mp >= 20 and random.random() < 0.6:
                result = ["Босс использует Темную бурю!"]
                for enemy in alive_enemies:
                    damage = int(self._strength * 1.2 + random.randint(5, 15))
                    result.append(enemy.take_damage(damage))
                self._mp -= 20
                return "\n".join(result)
            else:
                target = random.choice(alive_enemies)
                return self.attack(target)

        else:
            if self._mp >= 30 and random.random() < 0.8:
                result = ["Босс использует АПОКАЛИПСИС!"]
                for enemy in alive_enemies:
                    damage = int(self._strength * 1.8 + random.randint(10, 25))
                    result.append(enemy.take_damage(damage))
                self._mp -= 30
                return "\n".join(result)
            else:
                weakest = min(alive_enemies, key=lambda x: x.hp)
                return f"Босс атакует слабого! {self.attack(weakest)}"


class Battle:
    def __init__(self, party, boss):
        self.party = party
        self.boss = boss
        self.turn_count = 0

    def calculate_initiative(self):
        participants = [p for p in self.party if p.is_alive] + [self.boss]
        participants.sort(key=lambda x: x.initiative, reverse=True)
        return participants

    def party_is_alive(self):
        return any(member.is_alive for member in self.party)

    def process_turn(self, character, action=None, skill_index=None, item_index=None):
        if not character.is_alive:
            return f"{character.name} мертв!"

        result = []

        effect_result = character.process_effects()
        if effect_result:
            result.append(effect_result)

        if character == self.boss:
            action_result = self.boss.choose_action(self.party)
            result.append(action_result)
        else:
            if action == "attack":
                action_result = character.attack(self.boss)
                result.append(action_result)
            elif action == "skill" and skill_index is not None:
                if 0 <= skill_index < len(character.skills):
                    skill = character.skills[skill_index]
                    action_result = skill.use(character, [self.boss])
                    result.append(action_result)
                else:
                    result.append("Нет такого навыка!")
            elif action == "item" and item_index is not None:
                action_result = character.use_item(item_index)
                result.append(action_result)
            else:
                result.append(f"{character.name} пропускает ход")

        if character != self.boss and character.is_alive:
            character._mp = min(character._max_mp, character.mp + 2)

        return "\n".join(result)

    def get_battle_status(self):
        status = []
        status.append("=" * 40)
        status.append("СТАТУС БОЯ:")
        status.append(f"Ход: {self.turn_count}")
        status.append("ПАТИ:")
        for i, member in enumerate(self.party, 1):
            status.append(f"{i}. {member}")
        status.append(f"БОСС: {self.boss}")
        status.append(f"Фаза босса: {self.boss.phase}")
        status.append("=" * 40)
        return "\n".join(status)


def main():
    print("=== ПАТИ ПРОТИВ БОССА ===")

    party = []
    classes = {
        '1': ('Воин', Warrior),
        '2': ('Маг', Mage),
        '3': ('Лекарь', Healer)
    }

    print("Создай пати (3 персонажа):")
    for i in range(3):
        print(f"\nПерсонаж {i + 1}:")
        print("1. Воин")
        print("2. Маг")
        print("3. Лекарь")

        choice = input("Выбери класс: ").strip()
        if choice not in classes:
            choice = '1'

        name = input("Имя персонажа: ").strip()
        if not name:
            name = f"Герой {i + 1}"

        class_name, class_obj = classes[choice]
        party.append(class_obj(name))

    difficulty = input("Сложность (1-легко, 2-нормально, 3-тяжело): ").strip()
    if difficulty == '3':
        boss_level = 7
    elif difficulty == '2':
        boss_level = 5
    else:
        boss_level = 3

    boss = Boss("Злой Босс", boss_level)
    battle = Battle(party, boss)

    print("\n=== БОЙ НАЧИНАЕТСЯ! ===")

    while battle.party_is_alive() and boss.is_alive:
        battle.turn_count += 1
        print(f"\nХод {battle.turn_count}")
        print(battle.get_battle_status())

        initiative_order = battle.calculate_initiative()

        for character in initiative_order:
            if not character.is_alive:
                continue

            if character == boss:
                result = battle.process_turn(character)
                print(f"\nХод босса:")
                print(result)
            else:
                print(f"\nХод {character.name}:")
                print("1. Атака")
                print("2. Навык")
                print("3. Предмет")

                choice = input("Выбери действие: ").strip()

                if choice == "2":
                    print("Навыки:")
                    for i, skill in enumerate(character.skills):
                        print(f"{i + 1}. {skill.name} ({skill.mp_cost} MP)")
                    skill_choice = input("Выбери навык: ").strip()
                    try:
                        skill_index = int(skill_choice) - 1
                    except:
                        skill_index = 0
                    result = battle.process_turn(character, "skill", skill_index)
                elif choice == "3":
                    print("Предметы:")
                    for i, item in enumerate(character._inventory):
                        print(f"{i + 1}. {item.name}")
                    item_choice = input("Выбери предмет: ").strip()
                    try:
                        item_index = int(item_choice) - 1
                    except:
                        item_index = 0
                    result = battle.process_turn(character, "item", None, item_index)
                else:
                    result = battle.process_turn(character, "attack")

                print(result)

            if not boss.is_alive or not battle.party_is_alive():
                break

        if not boss.is_alive:
            print("\n=== ПОБЕДА! Босс повержен! ===")
            break
        elif not battle.party_is_alive():
            print("\n=== ПОРАЖЕНИЕ! Все герои мертвы! ===")
            break

    print("Игра окончена!")


if __name__ == "__main__":
    main()