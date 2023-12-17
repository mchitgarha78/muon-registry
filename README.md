# Muon Registry

This implementation represents Muon Registry node version of [pyfrost-mpc](https://github.com/SAYaghoubnejad/pyfrost-mpc) library to run DKGs via command-line and schedule a python script as a cron-job to renew DKG operation on expired DKGs with random party.


Muon Registry has the functionality of running DKGs for two types of node party:

- **Predefined party**: Registry uses a party list as an argument to run DKG.
- **Random party**: Using deployment app as an intermediary to get secure random seed for party selection and verify the party which is used for running DKG. 




## How to Setup

To create a virtual environment (`venv`) and install the required packages, run the following commands:

```bash
$ git clone https://github.com/mchitgarha78/muon-registry.git --recurse-submodules
$ cd muon-registry
$ virtualenv -p python3.10 venv
$ source venv/bin/activate
(venv) $ pip install pyfrost_mpc/
```

**Note:** The required Python version is `3.10`.

## How to Run

Two methods are avaiable to run DKGs:

```bash
(venv) $ python dkg_cmd.py predefined-party --app-name [Your app name] --threshold [threshold of the DKG] --party [party of the DKG]
(venv) $ python dkg_cmd.py random-party --app-name [Your app name] --threshold [threshold of the DKG] --party-number [Number of peerIds to choose]
```

For example, if you want to run DKG upon deployment app, you run this command:

```bash
(venv) $ python dkg_cmd.py predefined-party --app-name deployment --threshold 2 --party "['16Uiu2HAkv3kvbv1LjsxQ62kXE8mmY16R97svaMFhZkrkXaXSBSTq','16Uiu2HAkvumPB54FCBoNR8nh4aVBNhdv8sNAtt6GegL6aW2V5nCe','16Uiu2HAkw89MG4Myh5hitNPVTqPekkCwMzib4Jq6BD9rtQLvJSPy']"
```

And if you want to renew DKG operation, just add `rotation.sh` bash script to your cron-jobs with your arbitary configuration.

Don't forget to add execute permission to it using the following command:

```bash
(venv) $ chmod +x rotation.sh
```

