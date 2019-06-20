# -*- coding: utf-8 -*-

import subprocess

def transliterate(text):
    process = subprocess.Popen(['node', '-e', 'console.log(require(\"hebrew-transliteration\").transliterate("' + text + '"))'],
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, encoding='utf8')
    out, err = process.communicate()
    if err:
        print(err)
    return out