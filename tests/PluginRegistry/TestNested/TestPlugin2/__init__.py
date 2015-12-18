# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

def getMetaData():
    return {
        "plugin": {
            "name": "TestPlugin2",
            "api": 2
        }
    }

def register(app):
    app.registerTestPlugin("TestPlugin2")