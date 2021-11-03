# from iota import ProposedTransaction, Address, Tag, TryteString, Iota, Transaction
# from iota.crypto.types import Seed
import json
import pandapower as pp
import numpy as np
from numpy.random import rand
import pandas as pd
import os
import pprint
import time
from hashlib import sha256
import time
from bitcoinaddress import Wallet
from tqdm import tqdm
import argparse

from blockchain import Wrapper

from blockchain import Agent

def create_synthetic_data(d_steps, d_num_agents, d_t_gens):
    """ Create files with fake daata

        Args:
            d_steps (int): number of desired steps
            d_num_agents (int): number of agents in fake data
            d_t_gens(int): number of agents with no generation
        """
    demand_df = pd.DataFrame(np.random.uniform(low=30, high=35, size=(d_num_agents, d_steps)))
    price_df = pd.DataFrame(np.random.uniform(low=12, high=15, size=(d_num_agents, d_steps)))
    supply_df = pd.DataFrame(np.random.uniform(low=66, high=70, size=(d_num_agents, d_steps)))
    gens = np.random.choice(demand_df.index, size = (d_t_gens,), replace=False)
    for gen in gens:
        price_df.iloc[gen] = np.zeros((1, d_steps))
        supply_df.iloc[gen] = np.zeros((1, d_steps))
    return demand_df, price_df, supply_df

def single_sided_auction(node_data, supply, demand, price, agents):
    node_vec = []
    supply_vec = []
    supply_price = []
    demand = []
    ED = 0
    for node in node_data:
        node_vec.append(node['node'])
        supply_vec.append(node['supply'])
        supply_price.append(node['price'])
        demand.append(node['demand'])
        ED += node['demand']
    supply_df = pd.DataFrame(data = {'Agents': node_vec, 'Supply': supply_vec, 'Price': supply_price, 'Demand': demand})
    supply_df = supply_df.sort_values(by='Price')
    cum_supply = np.cumsum(supply_df['Supply'])
    supply_df['Cumsum'] = cum_supply
    for index, value in enumerate(supply_df.Cumsum):
        if value >= ED:
            break
    return supply_df, ED, supply_df.iloc[index]['Price']

def micro_grid_exec(step, supply, demand, price, agents):
    net = pp.create_empty_network()
    min_pu = 0.95
    max_pu = 1.05

    bus = []
    for index in range(len(agents)):
        bus.append(pp.create_bus(net, vn_kv=110, min_vm_pu=min_pu, max_vm_pu=max_pu))

    lines = []
    for index in range(len(agents)):
        if index < len(agents) - 1:
            lines.append(pp.create_line(net, bus[index], bus[index+1], length_km=1, std_type='149-AL1/24-ST1A 110.0'))
        else:
            lines.append(pp.create_line(net, bus[index], bus[0], length_km=1, std_type='149-AL1/24-ST1A 110.0'))

    for index in range(len(agents)):
        pp.create_load(net, bus[index], p_mw=supply_df['Demand'][index])

    gens = []
    for index in range(len(agents)):
        if supply.iloc[index][step] != 0:
            pp.create_gen(net, bus[index], p_mw=0, min_p_mw=0, max_p_mw=np.array(supply[step])[index], controllable=True, slack=True)

    pp.runpp(net)
    pf_result = net.res_gen

    return pf_result

def payment_setup(step, auction_price, wrapper, supply, demand, price, agents):
    power_per_agent = []
    for agent in agents:
        agent.get_node()
        demand = agent.get_demand()[step]
        try:
            supply = gen_dict[agent.get_node()]
        except:
            supply = agent.get_supply()[step]
        to_app = supply - demand
        if abs(to_app) < 0.00001:
            to_app = 0
        power_per_agent.append(to_app)

    to_earn = {}
    to_pay = {}
    for index, payment in enumerate(power_per_agent):
        if payment < 0:
            to_pay[index] = abs(payment)
        else:
            to_earn[index] = payment

    payment_info = {}
    for payer, balance in to_pay.items():
        payment_info[payer] = {'node': [], 'total': []}
        for earner, gain in to_earn.items():
            if gain > 0:
                if balance >= gain:
                    payment_info[payer]['node'].append(earner)
                    payment_info[payer]['total'].append(gain)
                    to_pay[payer] = to_pay[payer] - gain
                    to_earn[earner] = to_earn[earner] - gain
                elif balance < gain:
                    payment_info[payer]['node'].append(earner)
                    payment_info[payer]['total'].append(balance)
                    to_pay[payer] = to_pay[payer] - balance
                    to_earn[earner] = to_earn[earner] - balance
                    break

    gather_data = {}
    for index, agent in enumerate(agents):
        info_dict = {}
        info_dict['price'] = auction_price
        try:
            info_dict['node'] = payment_info[index]['node']
            info_dict['power'] = payment_info[index]['total']
            if dlt == "blockchain":
                info_dict['seller'] = agents[payment_info[index]['node'][0]].get_address()
        except:
            pass
        gather_data[index] = info_dict

    for index, agent in enumerate(agents):
        if dlt == "blockchain":
            data = gather_data[index]
            agent.set_payment_data(data)
        elif dlt == "iota":
            address = addresses_dict[index]['price_address'][step]
            data = gather_data[index]
            tx = ProposedTransaction(address=Address(address), message=TryteString.from_unicode(json.dumps(data)), tag=Tag('PRICE'),value=0)
            tx = api.prepare_transfer(transfers=[tx])
            result = api.send_trytes(tx['trytes'], depth=3, min_weight_magnitude=9)

    pay_nodes = set(nodes) - set(gen_nodes)
    for node in pay_nodes:
        if dlt == "blockchain":
            agents[node].pay_power(step, wrapper)
        elif dlt == 'iota':
            agents[node].pay_power(step)

def exec(dlt):
    d_steps_vec = [1]
    d_agents_vec = [50]
    results_df = pd.DataFrame(columns = ['steps', 'agents', 'dlt', 'mean', 'max', 'min'])
    for d_steps in d_steps_vec:
        for d_num_agents in d_agents_vec:
            d_t_gens = int(0.3 * d_num_agents)

            demand, price, supply = create_synthetic_data(d_steps, d_num_agents, d_t_gens)
            steps_vec = np.linspace(0, d_steps, d_steps + 1)

            times_vec = []
            num_agents = demand.shape[0]
            steps = demand.shape[1]

            a_series = (supply != 0).any(axis=1)
            new_df = supply.loc[a_series]
            gen_nodes = np.array(new_df.index)

            addresses = []
            for i in tqdm(range(0, num_agents)):
                wallet = Wallet()
                addresses.append(wallet.key.__dict__['mainnet'].__dict__['wif'])
            wrapper = Wrapper()
            agents = []
            print('Created addresses')
            for index in tqdm(range(0, num_agents)):
                agents.append(Agent(np.array(demand.iloc[index]),
                                   np.array(supply.iloc[index]),
                                   index, addresses[index],
                                   np.array(price.iloc[index]), wrapper))
            nodes = list(np.linspace(0,num_agents-1, num_agents, dtype=np.int))
            steps_vec = list(np.linspace(0,steps-1, steps, dtype=np.int))
            times_vec = []
            for step in tqdm(steps_vec):
                start = time.time()
                step_energy_info = []
                for index, agent in enumerate(agents):
                    node, info_dict = agent.publish_energy_info(step)
                    step_energy_info.append(info_dict)
                supply_df, ED, auction_price = single_sided_auction(step_energy_info,supply, demand, price, agents)
                pf_result = micro_grid_exec(step, supply, demand, price, agents)
                supply_df.set_index('Agents', inplace=True)
                gen_values = pf_result['p_mw']
                gen_dict = dict(zip(gen_nodes, gen_values))
                total_demand = sum(supply_df['Demand'])
                total_supply = sum(gen_dict.values())
                losses = total_supply - total_demand
                payment_setup(step, auction_price, wrapper, supply, demand, price, agents)
                wrapper.mine_unconfirmed_transactions()
                times_vec.append(time.time()-start)
            new_df = pd.DataFrame(data={'steps': [d_steps],
                                         'agents': [d_num_agents],
                                         'dlt': ['blockchain'],
                                         'mean': [np.mean(times_vec)],
                                         'max': [np.max(times_vec)],
                                         'min': [np.min(times_vec)]})
            results_df = results_df.append(new_df, ignore_index = True)

parser = argparse.ArgumentParser()
parser.add_argument("dlt", help="Select DLT to test",
                    type=str)
args = parser.parse_args()

exec(args.dlt)
