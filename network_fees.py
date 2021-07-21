import sys

sys.path.append("./scalecodec")
sys.path.append("./substrateinterface")

from substrateinterface import SubstrateInterface
from scalecodec.type_registry import load_type_registry_file

FILE = 'network_fees.csv'

substrate = SubstrateInterface('wss://mof2.sora.org', ss58_format=69,
                               type_registry=load_type_registry_file('custom_types.json'), type_registry_preset='default')


def get_event_param(event, param_idx):
    return event.value['params'][param_idx]['value']

def parse_block(block_num):
    result = []
    block_hash = substrate.get_block_hash(block_num)
    events = substrate.get_events(block_hash)
    
    for idx, e in enumerate(events):
        module = e.value['module_id']
        event = e.value['event_id']
        if module == 'XorFee' and event == 'FeeWithdrawn':
            extrinsic_id = e.value['extrinsic_idx']
            xor_total_fee = get_event_param(e, 1)
            xor_referrer_estimated = int(xor_total_fee * 0.1) # no events with this info, only estimation
            xor_burned_estimated = int(xor_total_fee * 0.4) # no events with this info, only estimation
            xor_dedicated_for_buy_back = 0
            val_burned = 0
            val_reminted_parliament = 0
            # there are free tx's, thus handled via check
            if xor_total_fee != 0:
                # 50% xor is exchanged to val
                xor_dedicated_for_buy_back = get_event_param(events[idx + 2], 2)
                if len(events) > idx + 9:
                    # exchanged val burned
                    event_with_val_burned = events[idx + 9]
                    # 10% burned val is reminted to parliament
                    event_with_val_reminted_parliament = events[idx + 10]
                    if event_with_val_burned.value['extrinsic_idx'] == extrinsic_id and event_with_val_reminted_parliament.value['extrinsic_idx'] == extrinsic_id:
                        if event_with_val_burned.value['event_id'] == 'Withdrawn' and event_with_val_reminted_parliament.value['event_id'] == 'Deposited':
                            # if this branch is not executed then exchange has failed, reserved 50% xor is burned
                            val_burned = get_event_param(event_with_val_burned, 2)
                            val_reminted_parliament = get_event_param(event_with_val_reminted_parliament, 2)
            result.append((xor_total_fee, xor_referrer_estimated, xor_burned_estimated, xor_dedicated_for_buy_back, val_burned, val_reminted_parliament))
    return result
    
def collect_network_fee_events():
    head_num = substrate.get_block_header()['header']['number']

    # NOTE: each line is individual extrinsic, therefore blocks numbers are repeated
    # NOTE: restarting script wipes existing data
    print("Writing to '%s'" % FILE)
    with open(FILE, 'w') as f:
        f.write('block_num, xor_total_fee, xor_referrer_estimated, xor_burned_estimated, xor_dedicated_for_buy_back, val_burned, val_reminted_parliament\n')
        for block_num in range(0, head_num):
            for elem in parse_block(block_num):
                print(str(block_num) + ', ' + ', '.join(str(x) for x in elem) + '\n')
                f.write(str(block_num) + ', ' + ', '.join(str(x) for x in elem) + '\n')
            if block_num % 100 == 0:
                print('Done: %d/%d\r' % (block_num, head_num), end='')
    print("\nDONE")

if __name__ == "__main__":
    collect_network_fee_events()
