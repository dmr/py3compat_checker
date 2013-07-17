from flask import Flask, redirect, url_for, session, request, jsonify, render_template, flash
from flask_oauthlib.client import OAuth
import logging
from pkg_resources import Requirement
from pkgtools.pypi import PyPIXmlRpc, real_name


logging.basicConfig(format='%(asctime)-15s %(message)s')


app = Flask(__name__)
app.debug = True
app.secret_key = 'development'


@app.route('/')
def index():
    context = {}
    return render_template('layout.html', **context)
    #return redirect(url_for('login'))


ALLOWED_EXTENSIONS = ('txt', '')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            # filename = secure_filename(file.filename)
            requirements_text = file.read()
            return render_template(
                'layout.html',
                package_compatibility=get_compatibility_dict(requirements_text)
            )
    flash("Please post a requirements.txt file. File had an invalid extension")
    return redirect(url_for('index'))


def get_compatibility_dict(requirements_text):
    package_compatibility = parse_list_of_requirements(requirements_text)
    for package_name in package_compatibility['packages']:
        is_compatible_info = None
        try:
            is_compatible_info = py3_compatibility_of_one_package(package_name)
        except Exception as exc:
            logging.error("Error checking compatibility of {0}: {1}".format(
                package_name, exc))
            pass
        package_compatibility['package_py3_compatibility'][package_name] = is_compatible_info
    return package_compatibility


def py3_compatibility_of_one_package(package_name):
    """ returns
    True if compatible,
    False if not,
    None if nothing is mentioned in the setup.py
    """
    if not package_name:
        raise ValueError("No package name specified!")
    package_real_name = real_name(package_name)
    pypi = PyPIXmlRpc()
    package_versions = pypi.package_releases(package_real_name)
    latest_version = package_versions[0]
    release = pypi.release_data(package_real_name, latest_version)

    # HACK: to avoid checking for 3.1, 3.2 etc, lets just str the classifiers
    # Original idea is from https://code.google.com/p/python3wos
    classifiers = str(release['classifiers'])

    ret = {'checked_version': latest_version}
    if 'Programming Language :: Python :: 3' in classifiers:
        ret.update({'compatible': True})
        return ret
    if 'Programming Language :: Python :: 2 :: Only' in classifiers:
        ret.update({'compatible': False})
        return ret
    ret.update({'compatible': None})
    return ret


def parse_list_of_requirements(requirements_text):
    package_compatibility = {
        'packages': set(),
        'ignored': set(),
        'package_py3_compatibility': {}
    }
    if requirements_text:
        requirements = requirements_text.splitlines()
        for line in requirements:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                req = Requirement.parse(line)
                package_compatibility['packages'].add(req.project_name)
            except ValueError:
                package_compatibility['ignored'].add(line)
    return package_compatibility


if __name__ == '__main__':
    # print get_compatibility_dict(open('../../requirements.txt', 'rb').read())
    app.run()
