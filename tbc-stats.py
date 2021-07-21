import sys
sys.path.append("./scalecodec")
sys.path.append("./substrateinterface")

from substrateinterface import SubstrateInterface
from scalecodec.type_registry import load_type_registry_file
from scalecodec import block
import math
import json

# __package__ = 'parse-substrate'

RESERVES_ACC = 'cnTQ1kbv7PBNNQrEb1tZpmK7eE2hQTwktcdewhc55bpkDrYBX'

VAL = '0x0200040000000000000000000000000000000000000000000000000000000000'
PSWAP = '0x0200050000000000000000000000000000000000000000000000000000000000'
DAI = '0x0200060000000000000000000000000000000000000000000000000000000000'
ETH = '0x0200070000000000000000000000000000000000000000000000000000000000'
SUPPLY = [PSWAP, VAL]
RESERVES = [ETH, DAI, VAL, PSWAP]
BLOCKS_TO_WAIT = 5

substrate = SubstrateInterface('wss://mof2.sora.org', ss58_format=69,
                               type_registry=load_type_registry_file('custom_types.json'), type_registry_preset='default')


def get_reserves(block_hash):
    reserves = []

    for asset in RESERVES:
        result = substrate.query('Tokens', 'Accounts', [
                                 RESERVES_ACC, asset], block_hash)
        reserves.append(result.value['free'])

    reserves_str = ', '.join(map(str, reserves))
    return reserves_str


def get_supply(block_hash):
    supply = []

    result = substrate.query(
        'Balances', 'TotalIssuance', block_hash=block_hash)
    supply.append(result.value)

    for asset in SUPPLY:
        result = substrate.query('Tokens', 'TotalIssuance', [
                                 asset], block_hash=block_hash)
        supply.append(result.value)

    supply_str = ', '.join(map(str, supply))
    return supply_str


def print_data(block_number):
    block_hash = substrate.get_block_hash(block_number)
    reserves = get_reserves(block_hash)
    supply = get_supply(block_hash)
    print('%d, %s, %s' % (block_number, supply, reserves))


def create_subscription_handler():
    last_block_number = 0

    def subscription_handler(obj, update_nr, subscription_id):
        nonlocal last_block_number

        block_number = obj['header']['number']
        last_block_to_parse = block_number - BLOCKS_TO_WAIT

        if last_block_number < last_block_to_parse:
            for i in range(last_block_number + 1, last_block_to_parse + 1):
                print_data(i)
            last_block_number = last_block_to_parse

    return subscription_handler


result = substrate.subscribe_block_headers(create_subscription_handler())
