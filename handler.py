from service.runner import Runner
import os



def handler(event, context):
    r = Runner()
    r.pipeline()
    print(event)


handler({}, {})