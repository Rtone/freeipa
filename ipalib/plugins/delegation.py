# Authors:
#   Rob Crittenden <rcritten@redhat.com>
#
# Copyright (C) 2010  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""
Group to Group Delegation

A permission enables fine-grained delegation of permissions. Access Control
Rules, or instructions (ACIs), grant permission to permissions to perform
given tasks such as adding a user, modifying a group, etc.

Group to Group Delegations grants the members of one group to update a set
of attributes of members of another group.

EXAMPLES:

 Add a self-service rule to allow users to manage their address:
   ipa selfservice-add --permissions=write --attrs=street,postalCode,l,c,st "User's manage their own address"

 When managing the list of attributes you need to include all attributes
 in the list, including existing ones. Add telephoneNumber to the list:
   ipa selfservice-mod --attrs=street,postalCode,l,c,st,telephoneNumber "User's manage their own address"

 Display our updated rule:
   ipa selfservice-show "User's manage their own address"

 Delete a rule:
   ipa selfservice-del "User's manage their own address"
"""

import copy
from ipalib import api, _, ngettext
from ipalib import Flag, Str, List
from ipalib.request import context
from ipalib import api, crud, errors
from ipalib import output
from ipalib import Object, Command

def convert_delegation(aci):
    """
    memberOf is in filter but we want to pull out the group for easier
    displaying.
    """
    filter = aci['filter']
    st = filter.find('memberOf=')
    if st == -1:
        raise errors.NotFound(reason=_('Delegation \'%(permission)s\' not found') % dict(permission=aci['aciname']))
    en = filter.find(')', st)
    membergroup = filter[st+9:en]
    aci['membergroup'] = membergroup

    return aci

def is_delegation(aciname):
    """
    Determine if the ACI is a Delegation ACI and raise an exception if it
    isn't.

    Return the result if it is a delegation ACI, adding a new attribute
    membergroup.
    """
    result = api.Command['aci_show'](aciname)['result']
    if 'filter' in result:
        result = convert_delegation(result)
    else:
        raise errors.NotFound(reason=_('Delegation \'%(permission)s\' not found') % dict(permission=aciname))
    return result


class delegation(Object):
    """
    Delegation object.
    """

    label = _('Delegation')

    takes_params = (
        Str('aciname',
            cli_name='name',
            label=_('Delegation name'),
            doc=_('Delegation name'),
            primary_key=True,
        ),
        List('permissions?',
            cli_name='permissions',
            label=_('Permissions'),
            doc=_('Comma-separated list of permissions to grant ' \
                '(read, write). Default is write.'),
        ),
        List('attrs',
            cli_name='attrs',
            label=_('Attributes'),
            doc=_('Comma-separated list of attributes'),
        ),
        Str('memberof',
            cli_name='membergroup',
            label=_('Member user group'),
            doc=_('User group to apply delegation to'),
        ),
        Str('group',
            cli_name='group',
            label=_('User group'),
            doc=_('User group ACI grants access to'),
        ),
    )

api.register(delegation)


class delegation_add(crud.Create):
    """
    Add a new delegation.
    """

    msg_summary = _('Added delegation "%(value)s"')

    def execute(self, aciname, **kw):
        if not 'permissions' in kw:
            kw['permissions'] = (u'write',)
        result = api.Command['aci_add'](aciname, **kw)['result']
        if 'filter' in result:
            result = convert_delegation(result)

        return dict(
            result=result,
            value=aciname,
        )

api.register(delegation_add)


class delegation_del(crud.Delete):
    """
    Delete a delegation.
    """

    has_output = output.standard_delete
    msg_summary = _('Deleted delegation "%(value)s"')

    def execute(self, aciname, **kw):
        is_delegation(aciname)
        result = api.Command['aci_del'](aciname, **kw)
        return dict(
            result=True,
            value=aciname,
        )

api.register(delegation_del)


class delegation_mod(crud.Update):
    """
    Modify a delegation.
    """

    msg_summary = _('Modified delegation "%(value)s"')

    def execute(self, aciname, **kw):
        is_delegation(aciname)
        result = api.Command['aci_mod'](aciname, **kw)['result']
        if 'filter' in result:
            result = convert_delegation(result)
        return dict(
            result=result,
            value=aciname,
        )

api.register(delegation_mod)


class delegation_find(crud.Search):
    """
    Search for delegations.
    """

    msg_summary = ngettext(
        '%(count)d delegation matched', '%(count)d delegations matched'
    )

    def execute(self, term, **kw):
        acis = api.Command['aci_find'](term, **kw)['result']
        results = []
        for aci in acis:
            try:
                if 'filter' in aci:
                    aci = convert_delegation(aci)
                    results.append(aci)
            except errors.NotFound:
                pass

        return dict(
            result=results,
            count=len(results),
            truncated=False,
        )

api.register(delegation_find)


class delegation_show(crud.Retrieve):
    """
    Display information about a delegation.
    """
    has_output_params = (
        Str('aci',
            label=_('ACI'),
        ),
    )

    def execute(self, aciname, **kw):
        result = is_delegation(aciname)
        return dict(
            result=result,
            value=aciname,
        )

api.register(delegation_show)
