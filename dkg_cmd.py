from registy import Registry
from config import REGISTRY_URL
import argparse
import trio


def main():
    parser = argparse.ArgumentParser(description='Registry Command-line.')
    
    subparsers = parser.add_subparsers(title='Commands', dest='operation', help='Choose an option')
    
    random_party = subparsers.add_parser('random-party', help = 'Requests a DKG with a random party')
    random_party.add_argument('--app-name', '-a', type=str, help='Name of the app.', required = True)
    random_party.add_argument('--threshold', '-t', type=int, help='Threshold number of the DKG.', required = True)
    random_party.add_argument('--party-number', '-n', type=int, help='Number of the nodes to choose from party.', required = True)
    random_party.add_argument('--total-node-number', '-T', type=int, help='Number of the nodes you ran.', required = True)
    random_party.set_defaults(func= trio.run)

    predefined_party = subparsers.add_parser('predefined-party', help = 'Requests a DKG with a predefined party.')
    predefined_party.add_argument('--app-name', '-a', type=str, help='Name of the app.', required = True)
    predefined_party.add_argument('--threshold', '-t', type=int, help='Threshold number of the DKG.', required = True)
    predefined_party.add_argument('--party', '-p', type=str, help='Party list of the nodes\' peerIds.')
    predefined_party.add_argument('--total-node-number', '-T', type=int, help='Number of the nodes you ran.', required = True)
    predefined_party.set_defaults(func= trio.run)
    args = parser.parse_args()
    registry = Registry(args.total_node_number, REGISTRY_URL)
    args.func(registry.run, args)

if __name__ == '__main__':
    main()