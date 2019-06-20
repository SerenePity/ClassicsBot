# -*- coding: utf-8 -*-
import traceback

import subprocess

def transliterate(text):
    try:
        process = subprocess.Popen(['node', '-e', 'console.log(require(\"node_modules/hebrew-transliteration\").transliterate("' + text + '"))'],
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, encoding='utf8')
        out, err = process.communicate()
    except:
        traceback.print_exc()
    print("In hebrew.transliterate()")
    if err:
        print(err)
    if out == "" or not out:
        return "Not found"
    return out

#transliterate("אֲדֹנָי שְׂפָתַי תִּפְתָּח וּפִי יַגִּיד תְּהִלָּתֶךָ׃")