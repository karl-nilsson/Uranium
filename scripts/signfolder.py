#!/usr/bin/env python3

import argparse
import json
import os
import sys
from typing import Optional, List

from UM.Logger import Logger
from UM.Trust import TrustBasics

# Default arguments, if arguments to the script are omitted, these values are used:
DEFAULT_PRIVATE_KEY_PATH = "../private_key.pem"
DEFAULT_TO_SIGN_FOLDER = "."
DEFAULT_IGNORE_SUBFOLDERS = ["__pycache__"]
DEFAULT_PASSWORD = ""


def signFolder(private_key_path: str, path: str, ignore_folders: List[str], optional_password: Optional[str]) -> bool:
    """Generate a signature for a folder (given a private key) and save it to a json signature file within that folder.

    - The signature file itself will be signed, this is saved in the 'root_manifest_signature'.
      This happens in a slightly different way in comparison to the other files:
      The key in this case is the hash of the alphabetized*, concatenated** name/hash pairs.
      (Not the entire file: as the self-sign is included in the manifest, this would cause an infinite recursion).
      *)  Where the name is the key as it appears in 'root-signatures', so 'src/b.py' will go _after_ 'c', because c < s
      **) For all keys in 'root-signatures': key0/hash0/key1/hash1/key2/hash2/... (without the slashes!)
    - On validation, any 'extra' files not in the ignored (cache) folders should also trigger failure.
    - Be careful, check if symlinks have been followed after signing!

    A json signature file for a folder looks like this:
    {
      "root_manifest_signature": "...<key in base-64>...",
      "root_signatures": {
        "text.txt": "...<key in base-64>...",
        "img.png": "...<key in base-64>...",
        "subfolder/text.txt": "...<key in base-64>..."
      }
    }

    Note that, within the file, the order of keys is not guaranteed: 'root_manifest_signature' may appear before or
    after 'root_signatures', and the order of keys within 'root_signatures' can be anything as long as the right hashes
    are associated with the right keys.

    See also 'Trust.py' in the main library and the related scripts; 'createkeypair.py', 'signfile.py' in this folder.

    :param private_key_path: Path to the file containing the private key.
    :param path: The folder to be signed.
    :param ignore_folders: Local cache folders (that should be deleted on restart of the app) can be ignored.
    :param optional_password: If the private key has a password, it should be provided here.
    :return: Whether a valid signature file has been generated and saved.
    """

    path = path if path not in ["", "."] else os.getcwd()
    password = None if optional_password == "" else optional_password
    private_key = TrustBasics.loadPrivateKey(private_key_path, password)
    if private_key is None:
        return False

    try:
        signatures = {}  # Dict[str, str]

        # Loop over all files in the folder:
        for root, dirnames, filenames in os.walk(path, followlinks = True):
            if os.path.basename(root) in ignore_folders:
                continue
            for filename in filenames:
                if filename == TrustBasics.getSignaturesLocalFilename() and root == path:
                    continue

                # Generate a signature for the current file:
                name_on_disk, name_in_data = TrustBasics.getFilePathInfo(path, root, filename)
                signature = TrustBasics.getFileSignature(name_on_disk, private_key)
                if signature is None:
                    Logger.logException("e", "Couldn't sign file '{0}'.".format(name_on_disk))
                    return False
                signatures[name_in_data] = signature

        # Make the self-signature for the whole 'self-signed' aspect of the manifest:
        self_signature = TrustBasics.getHashSignature(TrustBasics.getSelfSignHash(signatures), private_key)

        # Save signatures to json:
        wrapped_signatures = {
            TrustBasics.getRootSignatureCategory(): signatures,
            TrustBasics.getRootSignedManifestKey(): self_signature
        }

        json_filename = os.path.join(path, TrustBasics.getSignaturesLocalFilename())
        with open(json_filename, "w", encoding = "utf-8") as data_file:
            json.dump(wrapped_signatures, data_file, indent = 2)

        Logger.log("i", "Signed folder '{0}'.".format(path))
        return True

    except:  # Yes, we  do really want this on _every_ exception that might occur.
        Logger.logException("e", "Couldn't sign folder '{0}'.".format(path))
    return False


def mainfunc():
    """Arguments:

    `-k <filename>` or `--private <filename>` path to the private key
    `-f <path>` or `--folder <path>` path to the folder to be signed
    `-i <local-path>` or `--ignore <local-path>` sub-folders to be ignored (useful for cache files that'll be deleted)
    `-w <password>` or `--password <password>` if the private key file has a password, it should be specified like this
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--private", type = str, default = DEFAULT_PRIVATE_KEY_PATH)
    parser.add_argument("-f", "--folder", type = str, default = DEFAULT_TO_SIGN_FOLDER)
    parser.add_argument("-i", "--ignore", type = str, nargs = '+', default = DEFAULT_IGNORE_SUBFOLDERS)
    parser.add_argument("-w", "--password", type = str, default = DEFAULT_PASSWORD)
    args = parser.parse_args()
    signFolder(args.private, args.folder, args.ignore, args.password)


if __name__ == "__main__":
    sys.exit(mainfunc())
