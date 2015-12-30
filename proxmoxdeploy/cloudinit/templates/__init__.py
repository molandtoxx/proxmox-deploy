# proxmox-deploy is cli-based deployment tool for Proxmox
#
# Copyright (c) 2015 Nick Douma <n.douma@nekoconeko.nl>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see http://www.gnu.org/licenses/.

from proxmoxdeploy.questions import QuestionGroup, OptionalQuestionGroup, \
                        SpecificAnswerOptionalQuestionGroup, Question, \
                        IntegerQuestion, BooleanQuestion, EnumQuestion, \
                        NoAskQuestion, MultipleAnswerQuestion
from jinja2 import Environment, PackageLoader, Template
from paramiko import Agent, SSHException
import locale
import pytz

VALID_LOCALES = sorted(set(locale.locale_alias.values()))
VALID_KEYBOARD_LAYOUTS = [
    "af", "al", "am", "ara", "at", "az", "ba", "bd", "be", "bg", "br", "brai",
    "bt", "bw", "by", "ca", "cd", "ch", "cm", "cn", "cz", "de", "dk", "ee",
    "epo", "es", "et", "fi", "fo", "fr", "gb", "ge", "gh", "gn", "gr", "hr",
    "hu", "ie", "il", "in", "iq", "ir", "is", "it", "jp", "ke", "kg", "kh",
    "kr", "kz", "la", "latam", "lk", "lt", "lv", "ma", "mao", "md", "me", "mk",
    "ml", "mm", "mn", "mt", "mv", "nec_vndr/jp", "ng", "nl", "no", "np", "ph",
    "pk", "pl", "pt", "ro", "rs", "ru", "se", "si", "sk", "sn", "sy", "th",
    "tj", "tm", "tr", "tw", "tz", "ua", "us", "uz", "vn", "za"
]
VALID_TIMEZONES = sorted(pytz.common_timezones)

try:
    _agent = Agent()
    DEFAULT_SSH_KEYS = [
        "ssh {0}".format(key.get_base64()) for key in _agent.get_keys()
    ]
    _agent.close()
    del _agent

    if not DEFAULT_SSH_KEYS:
        DEFAULT_SSH_KEYS = None
except SSHException:
    DEFAULT_SSH_KEYS = None

QUESTIONS = QuestionGroup([
    ("_basic", QuestionGroup([
        ("vmid", IntegerQuestion("Virtual Machine id", min_value=100)),
        ("name", Question("Hostname (a FQDN is recommended)")),
    ])),
    ("_languages", QuestionGroup([
        ("locale", EnumQuestion("Locale", default="en_US.UTF-8", valid_answers=VALID_LOCALES)),
        ("timezone", EnumQuestion("Timezone", default="Europe/Amsterdam", valid_answers=VALID_TIMEZONES)),
        ("kb_layout", EnumQuestion("Keyboard layout", default="us", valid_answers=VALID_KEYBOARD_LAYOUTS)),
    ])),
    ("_security", QuestionGroup([
        ("ssh_pass_auth", NoAskQuestion("Allow SSH login using password", default=False)),
        ("ssh_root_keys", MultipleAnswerQuestion("SSH Public key for root user", default=DEFAULT_SSH_KEYS)),
        ("apt_update", BooleanQuestion("Run apt-get update after rollout", default=True)),
        ("apt_upgrade", BooleanQuestion("Run apt-get upgrade after rollout", default=False))
    ])),
    ("_network", OptionalQuestionGroup([
        ("configure_network", NoAskQuestion(question=None, default=True)),
        ("network_device", NoAskQuestion(question=None, default="eth0")),
        ("_static_network", SpecificAnswerOptionalQuestionGroup([
            ("ip_address", Question("IP Address")),
            ("subnet_mask", Question("Subnet Mask", default="255.255.255.0")),
            ("network_address", Question("Network Address")),
            ("broadcast_address", Question("Broadcast Address")),
            ("gateway_address", Question("Gateway Address")),
            ("dns_servers", Question("DNS Servers (space separated)"))
        ], optional_question=EnumQuestion(
            "Network type", default="dhcp", valid_answers=["static", "dhcp"]),
            specific_answer="static"
        ))
    ], optional_question=BooleanQuestion("Configure networking", default=True))),
    ("_misc", QuestionGroup([
        ("resize_rootfs", BooleanQuestion("Resize root filesystem", default=True)),
        ("packages", Question("Install extra packages (space separated))", default="")),
        ("commands", Question("Run commands after cloud init (space separated)", default=""))
    ]))
])


def ask_cloudinit_questions():
    global QUESTIONS
    QUESTIONS.ask_all()
    return QUESTIONS.flatten_answers()


def _generate_data(output_file, context, template_file, default_template):
    if not template_file:
        env = Environment(loader=PackageLoader("proxmoxdeploy.cloudinit"))
        template = env.get_template(default_template)
    else:
        template = Template(template_file.read())

    with open(output_file, "w") as output:
        output.write(template.render(context=context))


def generate_user_data(output_file, context, template_file=None):
    """
    Generates the user-data part of the "No Cloud" cloud-init approach.

    Parameters
    ----------
    output_file: str
        Filename where the user-data file will be created.
    context: dict
        Dict(-like) object where the required template variables can be looked
        up.
    template_file: file
        File to read the Jinja2 template to populate from. If not set, will load
        the default template. The file will be read to the end.
    """
    _generate_data(output_file, context, template_file, "user-data.j2")


def generate_meta_data(output_file, context, template_file=None):
    """
    Generates the meta-data part of the "No Cloud" cloud-init approach.

    Parameters
    ----------
    output_file: str
        Filename where the meta-data file will be created.
    context: dict
        Dict(-like) object where the required template variables can be looked
        up.
    template_file: file
        File to read the Jinja2 template to populate from. If not set, will load
        the default template. The file will be read to the end.
    """
    _generate_data(output_file, context, template_file, "meta-data.j2")
