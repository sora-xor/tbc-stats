import sys

sys.path.append("./scalecodec")
sys.path.append("./substrateinterface")

from substrateinterface import SubstrateInterface
from scalecodec.type_registry import load_type_registry_file

DAY = 14400
FILE = 'pswap_distr.csv'

substrate = SubstrateInterface('wss://mof2.sora.org', ss58_format=69,
                               type_registry=load_type_registry_file('custom_types.json'), type_registry_preset='default')


def get_event_param(event, param_idx):
    return event.value['params'][param_idx]['value']

def parse_block_with_distribution(block_num):
    '''
    Just in case more than one distributions happen in one block, returns list
    '''
    result = []
    block_hash = substrate.get_block_hash(block_num)
    events = substrate.get_events(block_hash)
    
    for idx, e in enumerate(events):
        module = e.value['module_id']
        event = e.value['event_id']
        if module == 'PswapDistribution' and event == 'FeesExchanged':
            if len(events) > idx + 4 and events[idx + 4].value['event_id'] == 'IncentiveDistributed':
                # buy back
                xor_spent = get_event_param(e, 3)
                pswap_gross_burn = get_event_param(e, 5)
                # burn all and remint
                pswap_reminted_lp = get_event_param(events[idx + 2], 2) # Currencies.Deposit
                pswap_reminted_parliament = get_event_param(events[idx + 3], 2) # Currencies.Deposit
                pswap_net_burn = pswap_gross_burn - pswap_reminted_parliament - pswap_reminted_lp
                result.append((xor_spent, pswap_gross_burn, pswap_reminted_lp, pswap_reminted_parliament, pswap_net_burn))
    return result


def get_all_blocks_with_distribution(end_block):
    '''
    Getting all possible blocks where fees exchange is triggered,
    note that some of blocks can have failed distributions due to e.g. no fees collected
    for particular pool.
    '''
    query_result = substrate.query_map('PswapDistribution', 'SubscribedAccounts')
    blocks_with_distributions = []
    for _, v in query_result:
        # block in which pool was created
        pool_created = v.value[3]
        for block_num in range(pool_created + DAY, end_block, DAY):
            blocks_with_distributions.append(block_num)
    
    return sorted(blocks_with_distributions)
    
def collect_pswap_distribution_events():
    head_num = substrate.get_block_header()['header']['number']
    
    blocks_with_distribution = get_all_blocks_with_distribution(head_num)

    with open(FILE, 'w') as f:
        f.write('block_num, xor_spent, pswap_gross_burn, pswap_reminted_lp, pswap_reminted_parliament, pswap_net_burn\n')
        for idx, block_num in enumerate(blocks_with_distribution):
            ok_distributions = parse_block_with_distribution(block_num)
            for elem in ok_distributions:
                print(str(block_num) + ', ' + ', '.join(str(x) for x in elem) + '\n')
                f.write(str(block_num) + ', ' + ', '.join(str(x) for x in elem) + '\n')
            if len(ok_distributions) > 0:
                print('Done: %d/%d\r' % (idx, len(blocks_with_distribution)), end='')
    print("\nSaved to '%s'" % FILE)

if __name__ == "__main__":
    collect_pswap_distribution_events()
