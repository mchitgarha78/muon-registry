# Muon Registry

This implementation represents Muon-Registry version of [pyfrost-mpc](https://github.com/SAYaghoubnejad/pyfrost-mpc) library to run DKGs via command-line and schedule a python script as a cron-job to renew DKG operation on expired DKGs for rotating their parties and updating the `apps.json` data.


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
After running these commands, you should get the json of the app data. The json format must be like this:
```json
{
    "c0134d04-3261-455c-a2a2-bd72e810734d":
    {
        "app_name": "deployment",
        "threshold": 1,
        "party": [
            "16Uiu2HAkv3kvbv1LjsxQ62kXE8mmY16R97svaMFhZkrkXaXSBSTq"
        ],
        "public_key": 299080140061782623340584255303244591137328916568463284608992368456986723412929,
        "public_shares": {
            "4714628304074915639012421846297078582633919588146527563135724408880052493726320426923515320": 
            299080140061782623340584255303244591137328916568463284608992368456986723412929
        },
        "is_predefined": true,
        "timestamp": 1702377303
    }
}
```
This json object is for predefined parties. DKGs with party rotaion have one more item named `deployment_signature`. after getting this json, Your can add it manually to the `apps.json` file.

Keep in mind to run a file server API (e.g., Nginx) that will return the content of `apps.json`.

And if you want to perform party rotation on expired DKGS and keep the `apps.json` updated, just add `rotation.sh` bash script to your cron-jobs with your arbitary configuration.

Don't forget to add execute permission to it using the following command:

```bash
(venv) $ chmod +x rotation.sh
```

