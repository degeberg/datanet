import string
import os.path

class TemplateManager:
    def __init__(self, template_dir):
        self.template_dir = os.path.abspath(template_dir) + '/'

    def load_template(self, name, vars={}):
        with open(self.template_dir + name, 'r') as f:
            tpl = f.read()

        return string.Template(tpl).safe_substitute(vars)
