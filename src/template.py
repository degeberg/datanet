import string

TEMPLATE_DIR='./templates/'

def load_template(name, vars={}):
    with open(TEMPLATE_DIR + name, 'r') as f:
        tpl = f.read()

    for var, value in vars.items():
        tpl = tpl.replace('{{'+var+'}}', str(value))

    return tpl
