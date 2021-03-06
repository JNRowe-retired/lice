from pkg_resources import (resource_stream, resource_listdir)
import argparse
import datetime
import re
import os
import subprocess
import sys

__version__ = "0.2"

LICENSES = []
for file in sorted(resource_listdir(__name__, '.')):
    if file.startswith('template-'):
        LICENSES.append(file[9:-4])

DEFAULT_LICENSE = "bsd3"


def clean_path(p):
    """ Clean a path by expanding user and environment variables and
        ensuring absolute path.
    """
    p = os.path.expanduser(p)
    p = os.path.expandvars(p)
    p = os.path.abspath(p)
    return p


def guess_organization():
    """ Guess the organization from `git config`. If that can't be found,
        fall back to $USER environment variable.
    """
    try:
        stdout = subprocess.check_output('git config --get user.name'.split())
        org = stdout.strip()
    except OSError:
        org = os.environ["USER"]
    return org


def load_file_template(path):
    """ Load template from the specified filesystem path.
    """
    if not os.path.exists(path):
        raise ValueError("path does not exist: %s" % path)
    with open(clean_path(path)) as infile:
        template = infile.read()
    return template


def load_package_template(license):
    """ Load license template distributed with package.
    """
    with resource_stream(__name__, 'template-%s.txt' % license) as licfile:
        content = licfile.read()
    return content


def extract_vars(template):
    """ Extract variables from template. Variables are enclosed in
        double curly braces.
    """
    keys = []
    for match in re.finditer(r"\{\{ (?P<key>\w+) \}\}", template):
        keys.append(match.groups()[0])
    return keys


def generate_license(template, context):
    """ Generate a license by extracting variables from the template and
        replacing them with the corresponding values in the given context.
    """
    for key in extract_vars(template):
        if key not in context:
            raise ValueError("%s is missing from the template context" % key)
        template = template.replace("{{ %s }}" % key, context[key])
    return template


def main():

    def valid_year(string):
        if not re.match(r"^\d{4}$", string):
            raise argparse.ArgumentTypeError("Must be a four digit year")
        return string

    parser = argparse.ArgumentParser(description='Generate a license')

    parser.add_argument('license', metavar='license', nargs="?", choices=LICENSES,
                       help='the license to generate, one of: %s' % ", ".join(LICENSES))
    parser.add_argument('-o', '--org', dest='organization', default=guess_organization(),
                       help='organization, defaults to .gitconfig or os.environ["USER"]')
    parser.add_argument('-p', '--proj', dest='project', default=os.getcwd().split(os.sep)[-1],
                       help='name of project, defaults to name of current directory')
    parser.add_argument('-t', '--template', dest='template_path',
                       help='path to license template file')
    parser.add_argument('-y', '--year', dest='year', type=valid_year,
                       default="%i" % datetime.date.today().year,
                       help='copyright year')
    parser.add_argument('--vars', dest='list_vars', action="store_true",
                       help='list template variables for specified license')

    args = parser.parse_args()

    # do license stuff

    license = args.license or DEFAULT_LICENSE

    # list template vars if requested

    if args.list_vars:

        if args.template_path:
            template = load_file_template(args.template_path)
        else:
            template = load_package_template(license)

        var_list = extract_vars(template)

        if var_list:
            sys.stdout.write("The %s license template contains the following variables:\n" % (args.template_path or license))
            for v in var_list:
                sys.stdout.write("  %s\n" % v)
        else:
            sys.stdout.write("The %s license template contains no variables.\n" % (args.template_path or license))

        sys.exit(0)

    # create context

    context = {
        "year": args.year,
        "organization": args.organization,
        "project": args.project,
    }

    if args.template_path:
        template = load_file_template(args.template_path)
    else:
        template = load_package_template(license)

    content = generate_license(template, context)
    sys.stdout.write(content)


if __name__ == "__main__":
    main()
