import bottle

@bottle.route('/')
def index():
    return 'TODO'

def webui():
    bottle.run(host='', port=8080)