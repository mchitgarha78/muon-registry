from registry_process import RegistryProcess

import argparse
import trio

def main():
    parser = argparse.ArgumentParser(description="Registry Command-line.")
    
    subparsers = parser.add_subparsers(title="Commands", dest="operation", help="Choose an option")
    dkg_parser = subparsers.add_parser("dkg", help = "Requests a DKG with a predefined or random party")
    dkg_parser.add_argument("--mode", "-m", type=str, 
                            help = "Type of the dkg request for the party selection (predefined or random).", required = True)
    dkg_parser.add_argument("--threshold", "-t", type=int, help="Threshold number of the DKG.", required = True)
    dkg_parser.add_argument("--app-name", "-a", type=str, help="Name of the app.", required = True)
    dkg_parser.add_argument("--party", "-p", type=str, help="Party list of the nodes' peerIds.", required = True)
    dkg_parser.add_argument("--node-number", "-n", type=int, help="Number of the nodes to choose from party in random party selection.")
    dkg_parser.set_defaults(func= trio.run)

    args = parser.parse_args()
    registry_process = RegistryProcess(args.node_number,'http://127.0.0.1:8050/v1')
    args.func(registry_process.run, args)

if __name__ == "__main__":
    main()