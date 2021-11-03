# IOTA - Agent class definition

class Agent:
    def __init__(self, demand, supply, node, publish_address, price_address, money_address, price):
        """ Initialize agent instance.

        Args:
            demand (list): list of floats with demand data
            supply (list): list of floats with supply. Ceros if no supply.
            node (float): number of the node.
            publish_address (list): list of iota.types.Address with the publish address.
            price_address (list): list of node's price addresses.
            money_address (list): list of node's money addresses.
            price (list): list of prices for supply offers.
        """
        self.demand = demand
        self.supply = supply
        self.node = node
        self.publish_address = publish_address
        self.price_address = price_address
        self.money_address = money_address
        self.consumption = demand-supply
        self.price = price

    def publish_info(self, data, address):
        """ Send transaction with data to specified address

        Args:
            data (dict): information to be sent.
            address (iota.types.Address): Destination address for information
        """
        # Build TX object
        tx = ProposedTransaction(
            address = Address(address),
            message = TryteString.from_unicode(json.dumps(data)),
            tag = Tag('INFO'),
            value = 0)
        # Send information
        tx = api.prepare_transfer(transfers=[tx])
        try:
            result = api.send_trytes(tx['trytes'], depth=3, min_weight_magnitude=9)
        except:
            pass
        return result

    def pay_power(self, step):
        """ Send power payment

        Args:
            step (float): step running at the moment.
        """
        unpack_data = self.check_address(step, 'price')
        for index, node in enumerate(unpack_data[0]['node']):
            data_to_send = {'payment': unpack_data[0]['price']*unpack_data[0]['power'][index]}
            address = self.address_dict[node]['money_address'][step]
            self.publish_info(data_to_send, address)

    def check_address(self, step, address_type):
        """ Recover information from address.

        Args:
            step (float): Step running at the moment.
            address_type (str): Vector code to look for the address
        """

        if address_type == 'price':
            address = self.price_address[step]
        elif address_type == 'money':
            address = self.money_address[step]

        transactions = api.find_transactions(addresses=[address,])

        hashes = []
        for txhash in transactions['hashes']:
            hashes.append(txhash)

        trytes = api.get_trytes(hashes)['trytes']

        parts = []
        for trytestring in trytes:
            tx = Transaction.from_tryte_string(trytestring)
            parts.append((tx.current_index, tx.signature_message_fragment))

        parts.sort(key=lambda x: x[0])

        full_message = TryteString.from_unicode('')

        retrieved_data = []
        for index, part in parts:
            try:
                retrieved_data.append(json.loads(part.decode(errors='ignore')))
            except:
                pass
        return retrieved_data

    def publish_energy_info(self, step):
        agents_info = {}
        agents_info['node'] = self.node
        agents_info['demand'] = self.demand[step]
        agents_info['supply'] = self.supply[step]
        agents_info['consumption'] = self.demand[step] - self.supply[step]
        agents_info['price'] = self.price[step]

        return self.node, agents_info

    def get_demand(self):
        # Visualize demand
        return self.demand

    def get_supply(self):
        # Visualize supply
        return self.supply

    def get_node(self):
        # Visualize node
        return self.node

    def get_price_address(self):
        # Visualize price address
        return self.price_address

    def get_money_address(self):
        # Visualize money address
        return self.money_address

    def get_consumption(self):
        # Visualize consumption
        return self.consumption

    def get_prices(self):
        # Visualize price
        return self.price

    def assign_address_dict(self, address_dict):
        """ Assign address dict to node

        Args:
            address_dict (dict): With known addresses for each node (price and money) and publish addresses
        """
        self.address_dict = address_dict
