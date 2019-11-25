"""Handlers to parse raw packets from PwnAdventure 3 game.
"""
import struct
from functools import wraps
from typing import Any, Callable, Iterable, Mapping, Tuple

import helpers

# String to prepend to handler messages to indicate packet origin
DIRECTION_FORMAT = {
    helpers.ConnectionType.CLIENT: '-->>',
    helpers.ConnectionType.SERVER: '<<--'
}


def format(func: Callable[[bytes], Tuple[bytes, str]]) -> \
        Callable[[Iterable, Mapping[str, Any]], bytes]:
    """Decorator to filter printed parsed messages and for prepending origin.

    func should be a handler function to parse byte arrays.

    Args:
        func (Callable[[bytes], Tuple[bytes, str]]): handler to wrap

    Returns:
        Callable[[Iterable, Mapping[str, Any]], bytes]: wrapped handler
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        origin = kwargs.pop('origin', helpers.ConnectionType.CLIENT)
        direction = DIRECTION_FORMAT.get(origin, '???')
        data, message = func(*args, **kwargs)
        if func.__name__ not in NO_PRINT:
            print(f'[{direction}] {message}')
        return data

    return wrapper


@format
def handle_ack(data: bytes) -> Tuple[bytes, str]:
    """NOOP handler.

    Do nothing.

    Args:
        data (bytes): NOOP packet.

    Returns:
        Tuple[bytes, str]: next data segment and empty message.
    """
    return data, ''


@format
def handle_position(data: bytes) -> Tuple[bytes, str]:
    """Parse position packet to extract x,y,z coordinates.

    Args:
        data (bytes): position packet

    Returns:
        Tuple[bytes, str]: next data segment and position message
    """
    x, y, z = struct.unpack('fff', data[0:3 * 4])
    return data[20:], f'Current Position (x,y,z): {x} {y} {z}'


@format
def handle_jump(data: bytes) -> Tuple[bytes, str]:
    """Parse jump packet to determine whether character is jumping.

    Args:
        data (bytes): jump packet

    Returns:
        Tuple[bytes, str]: next data segment and jump message
    """
    jumping = struct.unpack('?', data[:1])[0]
    return data[1:], 'Jumping' if jumping else 'Falling'


@format
def handle_sneak(data: bytes) -> Tuple[bytes, str]:
    """Parse sneak packet to determine whether character is sneaking.

    Args:
        data (bytes): sneak packet

    Returns:
        Tuple[bytes, str]: next data segment and sneak message
    """
    sneaking = not(struct.unpack('?', data[:1])[0])
    return data[1:], 'Sneaking' if sneaking else 'Done sneaking'


@format
def handle_slot_select(data: bytes) -> Tuple[bytes, str]:
    """Parse slot packet to get new selected slot.

    Args:
        data (bytes): slot packet

    Returns:
        Tuple[bytes, str]: next data segment and slot message
    """
    new_slot = struct.unpack('B', data[:1])[0]
    return data[1:], f'New slot: {new_slot}'


@format
def handle_shoot(data: bytes) -> Tuple[bytes, str]:
    """Parse shoot packet to get name and direction of weapon shot.

    Args:
        data (bytes): shoot packet

    Returns:
        Tuple[bytes, str]: next data segment and shot information
    """
    length = struct.unpack('H', data[:2])[0]
    name = data[2:length+2]
    direction = struct.unpack('fff', data[length+2:length+2+12])
    return data[2+length:], f'Shot {name.decode()} in direction: {direction}'


@format
def handle_chat(data: bytes) -> Tuple[bytes, str]:
    """Parse chat packet to get chat message.

    Args:
        data (bytes): chat packet

    Returns:
        Tuple[bytes, str]: next data segment and chat message
    """
    length = struct.unpack('H', data[:2])[0]
    message = data[2:2+length].decode(helpers.ENCODING)
    return data[2+length:], f'Sent message: "{message}"'


@format
def handle_actor_drop(data: bytes) -> Tuple[bytes, str]:
    """Parse actor drop packet to get actor information.

    Message displays actor name and drop position.

    If the actor is a "Drop" object, send loot packet to server
    to automatically pick it up.

    Args:
        data (bytes): actor drop packet

    Returns:
        Tuple[bytes, str]: next data segment and actor information
    """
    # TODO: reverse first 9 bytes
    item_id = struct.unpack('I', data[:4])[0]
    unknown = struct.unpack('I', data[4:8])[0]  # noqa: F841
    unknown2 = data[9]  # noqa: F841
    item_name_length = struct.unpack('H', data[9:11])[0]
    item_name = data[11:11+item_name_length].decode(helpers.ENCODING)
    x, y, z = struct.unpack('fff',
                            data[11+item_name_length:11+item_name_length+3*4])

    message = f'[{item_id}] {item_name} dropped at: {x} {y} {z}'

    # Pick up drops automatically
    if "Drop" in item_name:
        message += f'\n\t;) Auto-looting {item_id}'
        packet = struct.pack('=HI', 0x6565, item_id)
        helpers.PACKET_QUEUE.put(packet)
    # TODO: not sure about last few bytes
    return data[11+item_name_length+3*4:], message


@format
def handle_region_change(data: bytes) -> Tuple[bytes, str]:
    """Parse region-change packet to get region name.

    Drop positions of initial actors, like GoldenEggs, is also revealed.

    Args:
        data (bytes): region-change packet

    Returns:
        Tuple[bytes, str]: next data segment and region-change information
    """
    region_name_length = struct.unpack('H', data[:2])[0]
    region_name = data[2:2+region_name_length]
    return (data[2+region_name_length:],
            f'Changing to region: {region_name.decode().upper()}')


@format
def handle_item_acquire(data: bytes) -> Tuple[bytes, str]:
    """Parse item-acquire packet to get information about item.

    For example, indicate the type and amount of ammo received by a Drop.

    Args:
        data (bytes): item-acquire packet

    Returns:
        Tuple[bytes, str]: next data segment and item-acquire information
    """
    item_name_length = struct.unpack('H', data[:2])[0]
    item_name = data[2:2+item_name_length].decode(helpers.ENCODING)
    amount = struct.unpack('I',
                           data[2+item_name_length:2+item_name_length+4])[0]
    return data[2+item_name_length+4:], f'Received {amount} {item_name}'


@format
def handle_item_pickup(data: bytes) -> Tuple[bytes, str]:
    """Parse item-pickup packet to get ID of item picked up.

    This packet can be used to implement auto-looting.

    Args:
        data (bytes): item-pickup packet

    Returns:
        Tuple[bytes, str]: next data segment and item ID
    """
    item_id = struct.unpack('I', data[:4])[0]
    return data[4:], f'Picked up item with ID {item_id}'


@format
def handle_reload(data: bytes) -> Tuple[bytes, str]:
    """Parse reload packet to get weapon reloaded and type and amount of ammo.

    This packet can also be used to implement auto-reloading.

    Args:
        data ([type]): [description]

    Returns:
        [type]: [description]
    """
    try:
        weapon_name_length = struct.unpack('H', data[:2])[0]
        weapon_name = data[2:2+weapon_name_length].decode(helpers.ENCODING)
        ammo_name_length = struct.unpack('H',
                                         data[2+weapon_name_length:2+weapon_name_length+2])[0]  # noqa: E501
        ammo_name = data[2+weapon_name_length+2:2+weapon_name_length+2+ammo_name_length].decode(helpers.ENCODING)  # noqa: E501
        ammo_count = struct.unpack('I',
                                   data[2+weapon_name_length+2+ammo_name_length:2+weapon_name_length+2+ammo_name_length+4])[0]  # noqa: E501
        message = f'Reloaded {weapon_name} with {ammo_count} {ammo_name}'
        rdata = data[2+weapon_name_length+2+ammo_name_length+4:]
    except UnicodeDecodeError:
        # Empty reload packet is sent when we need to reload
        message = 'Need to reload!'
        rdata = data
    return rdata, message


@format
def handle_health(data: bytes) -> Tuple[bytes, str]:
    """Parse health packet to get amount of HP for actors.

    Args:
        data (bytes): health packet

    Returns:
        Tuple[bytes, str]: next data segment and actor HP
    """
    actor_id, hp = struct.unpack('Ih', data[:6])
    return data[6:], f'Actor {actor_id} has {hp} HP'


@format
def handle_mana(data: bytes) -> Tuple[bytes, str]:
    """Parse mana packet to get amount of mana player has.

    Args:
        data (bytes): mana packet

    Returns:
        Tuple[bytes, str]: next data segment and player mana
    """
    mana = struct.unpack('H', data[:2])[0]
    return data[2:], f'Player has {mana} mana'


@format
def handle_ps(data: bytes) -> Tuple[bytes, str]:
    """UNKNOWN

    Args:
        data (bytes): ps packet

    Returns:
        Tuple[bytes, str]: next data segment and ps message
    """
    # TODO seems to happen when enemies are near
    return data[28:], ''


@format
def handle_state(data: bytes) -> Tuple[bytes, str]:
    """Parse actor state packet to get state of actors.

    Args:
        data ([type]): state packet

    Returns:
        Tuple[bytes, str]: next data segment and actor state
    """
    actor_id, state_length = struct.unpack('IH', data[:6])
    state = data[6:6+state_length].decode(helpers.ENCODING)
    return data[6+state_length:], f'Actor {actor_id} in {state} state'


@format
def handle_attack(data: bytes) -> Tuple[bytes, str]:
    """Parse attack packet to get actor that attacked a victim and the attack.

    Args:
        data (bytes): attack packet

    Returns:
        Tuple[bytes, str]: next data segment and attack information
    """
    attacker_id, attack_length = struct.unpack('IH', data[:6])
    attack = data[6:6+attack_length].decode(helpers.ENCODING)
    victim_id = struct.unpack('I', data[6+attack_length:6+attack_length+4])[0]
    return (data[6+attack_length+4:],
            f'Actor {attacker_id} performed "{attack}" on Actor {victim_id}')


@format
def handle_loaded_ammo(data: bytes) -> Tuple[bytes, str]:
    """Parse loaded ammo packet after firing weapon to get amount left.

    Implements auto-reloading by sending an empty reload packet once the
    loaded ammo is 0.

    Args:
        data (bytes): loaded ammo packet

    Returns:
        Tuple[bytes, str]: next data segment and amount of ammo loaded
    """
    weapon_name_length = struct.unpack('H', data[:2])[0]
    weapon_name = data[2:2+weapon_name_length].decode(helpers.ENCODING)
    loaded_ammo = struct.unpack('I',
                                data[2+weapon_name_length:2+weapon_name_length+4])[0]  # noqa: E501
    message = f'{weapon_name} has {loaded_ammo} shots remaining'
    if loaded_ammo == 0:
        message += '\n\t;) Auto-reloading'
        packet = struct.pack('>H', 0x726c)
        helpers.PACKET_QUEUE.put(packet)
    return data[2+weapon_name_length+4:], message


# Functions to handle each packet ID (keys)
PACKET_HANDLERS = {
    b'\x00\x00': handle_ack,
    b'mv': handle_position,
    b'jp': handle_jump,
    b'rn': handle_sneak,
    b's=': handle_slot_select,
    b'*i': handle_shoot,
    b'#*': handle_chat,
    b'mk': handle_actor_drop,
    b'ch': handle_region_change,
    b'cp': handle_item_acquire,
    b'ee': handle_item_pickup,
    b'rl': handle_reload,
    b'++': handle_health,
    b'ma': handle_mana,
    b'ps': handle_ps,
    b'st': handle_state,
    b'tr': handle_attack,
    b'la': handle_loaded_ammo
}
# Functions that @format decorator should filter and refuse to print
NO_PRINT = {'handle_ack', 'handle_position', 'handle_ps', 'handle_mana'}


def parse(data: bytes, port: int, origin: helpers.ConnectionType):
    """Route packet data handlers to parse into readable information.

    Args:
        data (bytes): packet of raw bytes to parse
        port (int): port that client that sent packet is listening on
        origin (constants.ConnectionType): type of connection packet
            originated from
    """
    # Ignore packets from master server... game server is more interesting
    if port == helpers.MASTER_PORT:
        return
    # Iteratively parse packet data until nothing is left to parse
    reads = 0
    while len(data) >= 2:
        reads += 1
        pid = data[:2]
        handler = PACKET_HANDLERS.get(pid, None)
        if handler:
            # Parse data without packet id prepended
            # Returned data will be parsed next iteration
            data = handler(data[2:], origin=origin)
        else:
            # This packet doesn't have a handler
            # Print it once for inspection
            if reads <= 1:
                print(f'[{pid}] - {data}\n')
            # Remove the first byte and try parsing again later
            data = data[1:]
