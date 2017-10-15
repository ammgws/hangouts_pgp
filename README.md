# hangouts_pgp
Command line interface for Hangouts with all messages encrypted using PGP.

##### Requirements
* GMail or Google Apps account which can use Hangouts
* PGP key for both user and client
* Python 3.6+

##### Installation
```
git clone https://github.com/ammgws/hangouts_pgp.git
cd hangouts_pgp
pip install -r requirements.txt
```

##### Before Use
1. Go to [Google APIs](https://console.developers.google.com/apis/) and generate secret client ID/password.
2. Fill in values in `config.ini`

##### Usage
```
Usage: hangouts_pgp.py [OPTIONS]

  TODO

Options:
  --config-path PATH  Path to directory containing config file. Defaults to XDG config dir.
  --cache-path PATH   Path to directory to store logs and such. Defaults to XDG cache dir.
  --help              Show this message and exit.
```
