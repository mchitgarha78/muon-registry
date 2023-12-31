# Muon Registry

This implementation represents Muon-Registry version of [pyfrost](https://github.com/SAYaghoubnejad/pyfrost) library to run DKGs via command-line and schedule a python script as a cron-job to renew DKG operation on expired DKGs for rotating their parties and updating the `apps.json` data. Muon-Registry along the [Muon-Node](https://github.com/mchitgarha78/muon-node), the [Muon-SA](https://github.com/mchitgarha78/muon-sa), and Muon-Apps runner ([python apps runner](https://github.com/mchitgarha78/muon-py-apps) and [js apps runner](https://github.com/mchitgarha78/muon-js-apps/tree/main)) represent the core of the Muon network to deploy and run apps and issue a distributed signature. For more insight on the Muon network, please read our [document](https://github.com/mchitgarha78/muon-node/wiki) describing the main functionalities of the muon system.



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
(venv) $ pip install -r requirements.txt
```

**Note:** The required Python version is `3.10`.

After these installations, configure `.env` file. The file `.env.example` has the example of thie environment variables. So you can type the following command:
```bash
(venv) $ cp .env.example .env
```

Change your settings in the `.env` file:
```
PRIVATE_KEY=<your-registry-private>
PORT=5038
HOST=0.0.0.0
APPS_LIST_URL=<your-apps-url>
```

You also need to configure your `nodes.json` file in `abstracts` directory:

```bash
(venv) $ cp ./abstracts/nodes.json.example ./abstracts/nodes.json
```

Get your nodes data and add it to `nodes.json` file. 


## How to Run

Two methods are available to run DKGs:

```bash
(venv) $ python dkg_cmd.py predefined-party --app-name [Your app name] --threshold [threshold of the DKG] --party [party of the DKG]
(venv) $ python dkg_cmd.py random-party --app-name [Your app name] --threshold [threshold of the DKG] --party-number [Number of nodeIds to choose]
```

For example, if you want to run DKG upon deployment app, you run this command:

```bash
(venv) $ python dkg_cmd.py predefined-party --app-name deployment --threshold 2 --party 1,2,3 
```
After running these commands, you should get the json of the app data. The json format must be like this:
```json
{
    "f4d5b4f9-ed74-4954-9fd2-b4766c0b4c6a": {
        "app_name": "deployment",
        "threshold": 1,
        "party": {
            "1": "16Uiu2HAkv3kvbv1LjsxQ62kXE8mmY16R97svaMFhZkrkXaXSBSTq"
        },
        "public_key": 296768544575062889523639571945738322985742122100051520084729374865199995195726,
        "public_shares": {
            "1": 296768544575062889523639571945738322985742122100051520084729374865199995195726
        },
        "is_predefined": true,
        "timestamp": 1703318284
    }
}
```
This json object is for predefined parties. DKGs with party rotaion have one more item named `deployment_signature`. After getting this json, you can add it manually to the `apps.json` file.

Keep in mind to run a file server API (e.g., Nginx) that will return the content of `apps.json` and address it when running Muon Nodes and Muon SAs.

And if you want to perform party rotation on expired DKGs and keep the `apps.json` updated, simply add the `rotation.sh` bash script to your cron jobs with your arbitrary configuration.

Don't forget to add execute permission to the bash script using the following command:

```bash
(venv) $ chmod +x rotation.sh
```

