import datetime as dt
import logging
import os.path
from configparser import ConfigParser
from pathlib import Path
from time import sleep
# Third party
import click
import gnupg
from hangoutsclient import HangoutsClient


APP_NAME = 'hangouts_pgp'


class GPGKeyNotFound(Exception):
    pass


class PGPHangouts(HangoutsClient):
    def __init__(self, gpg, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpg = gpg

    def message(self, sender_jid, msg):
        msg = pgp_formatter(msg, 'add')
        try:
            decrypted = self.gpg.decrypt(msg)
            if decrypted.ok:
                decrypted = str(decrypted)
                sender_name = self.client_roster[sender_jid]['name']
                click.secho(f'{sender_name}: ', fg='green', nl=False)
                click.echo(f'{decrypted}')
            else:
                logging.warning(f'Decryption failed: "{decrypted.status}"')
        except ValueError:
            logging.warning(f'Decryption failed: "{decrypted.status}"')

        self.last_received_from = sender_jid


def pgp_formatter(msg, action):
    header = '-----BEGIN PGP MESSAGE-----\n\n'
    footer = '\n-----END PGP MESSAGE-----\n'
    if action == 'add':
        msg = f'{header}{msg}{footer}'
    elif action == 'strip':
        msg = msg.replace(header, '').replace(footer, '')

    return msg


def create_dir(ctx, param, directory):
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    return directory


@click.command()
@click.option(
    '--config-path',
    type=click.Path(),
    default=os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), APP_NAME),
    callback=create_dir,
    help='Path to directory containing config file. Defaults to XDG config dir.',
)
@click.option(
    '--cache-path',
    type=click.Path(),
    default=os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), APP_NAME),
    callback=create_dir,
    help='Path to directory to store logs and such. Defaults to XDG cache dir.',
)
def main(config_path, cache_path):
    """TODO
    """
    configure_logging(cache_path)

    config_file = os.path.join(config_path, 'config.ini')
    logging.debug('Using config file: %s.', config_file)
    config = ConfigParser()
    config.read(config_file)

    client_id = config.get('Hangouts', 'client_id')
    client_secret = config.get('Hangouts', 'client_secret')
    token_file = os.path.join(cache_path, 'hangouts_cached_token')
    if not os.path.isfile(token_file):
        Path(token_file).touch()

    gpg_dir = os.getenv('GNUPGHOME', os.path.expanduser('~/.gnupg'))
    gpg = gnupg.GPG(gnupghome=gpg_dir, keyring=os.path.join(gpg_dir, 'pubring.kbx'))
    recipient = config.get('GPG', 'recipient')
    try:
        gpg.list_keys().key_map[recipient]
    except KeyError:
        logging.error('Recipient not found in GPG keyring.')
        click.secho(f'Could not find recipient fingerprint ({recipient}) in your GPG keyring.', fg='red')
        click.echo('Try checking `gpg --list-keys`.')
        return 1

    hangouts = PGPHangouts(gpg, client_id, client_secret, token_file, send_only=False)
    if hangouts.connect():
        hangouts.process(block=False)
        sleep(5)  # Need time for Hangouts roster to update.
    else:
        logging.error('Unable to connect to Hangouts.')

    for contact in hangouts.contacts_list:
        click.echo(contact['name'])

    while True:
        message = click.prompt('', prompt_suffix='')
        message = gpg.encrypt(message, recipient)
        if message.ok:
            message = pgp_formatter(str(message), 'strip')
            hangouts.send_to([hangouts.last_received_from, ], message)
        else:
            logging.warning(f'Encryption failed: "{message.status}"')

    hangouts.disconnect()


def configure_logging(log_dir):
    # Configure root logger. Level 5 = verbose to catch mostly everything.
    logger = logging.getLogger()
    logger.setLevel(level=5)

    log_folder = os.path.join(log_dir, 'logs')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder, exist_ok=True)

    log_filename = f'{APP_NAME}_{dt.datetime.now().strftime("%Y%m%d_%Hh%Mm%Ss")}.log'
    log_filepath = os.path.join(log_folder, log_filename)
    log_handler = logging.FileHandler(log_filepath)

    log_format = logging.Formatter(
        fmt='%(asctime)s.%(msecs).03d %(name)-12s %(levelname)-8s %(message)s (%(filename)s:%(lineno)d)',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log_handler.setFormatter(log_format)
    logger.addHandler(log_handler)
    # Lower requests module's log level so that OAUTH2 details aren't logged
    logging.getLogger('requests').setLevel(logging.WARNING)
    # Quieten SleekXMPP output
    # logging.getLogger('sleekxmpp.xmlstream.xmlstream').setLevel(logging.INFO)


if __name__ == '__main__':
    main()
